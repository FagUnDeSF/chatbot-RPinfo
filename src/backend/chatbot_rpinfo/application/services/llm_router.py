"""LLM router enforcing NIVEL-4 anti-fallback-silencioso (AP-2 LLM CRITICAL).

This router is the single canonical entry point for choosing which provider
gets `render_premises` for each request. It enforces 3 hard rules from
ADR-0005 + V5 §6 + V5 cross-security `aprovada-com-mitigacao-revisada`:

1. Haiku NEVER silently falls back to Sonnet. Sonnet is chosen ONLY when
   BOTH (a) explicit opt-in flag (header `X-LLM-Escalate: sonnet` or body
   `escalate=sonnet`) AND (b) gate-eval cache returns PASS for the
   `(prompt_version, intent_kind)` tuple within 24h. Otherwise Haiku is
   kept and the response carries `escalation_granted=false`.
2. Stub-deterministico is selected ONLY in 3 enumerated hard-triggers
   (V5 §2.1): provider down (3 consecutive 5xx/timeout in 60s) OR budget
   exceeded (HTTP 429 quota) OR forced-by-admin via `X-Force-Provider:
   stub-deterministico` with RBAC restricted to ADMIN_TECNICO.
3. Erro Haiku NEVER triggers Haiku->Sonnet swap. Erro Haiku triggers
   fallback to stub-deterministico with explicit signal (header
   `X-LLM-Fallback: stub-deterministico` + response payload field
   `fallback_active=true` + audit `fallback_reason` enumerated).

The router also tracks Haiku failure window (3-in-60s) and budget-exceeded
state in-process. In production this state is shared via a persistence
layer; for Sprint 002 Fase 1 the in-process state is sufficient (single
process; restart resets the window which is conservative).
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from chatbot_rpinfo.application.services.llm_provider import (
    MODEL_HAIKU_4_5,
    MODEL_SONNET_4_5,
    PROMPT_VERSION_V020,
    AnthropicLlmProvider,
    LlmProvider,
    StubDeterministicLlmProvider,
)
from chatbot_rpinfo.domain.entities import FallbackReason, InternalRole, QaIntentKind


class EscalationOutcome(StrEnum):
    """Outcome canonico do path de escalation Haiku -> Sonnet.

    NIVEL-4-OBS-2 (TL §2 parecer S2-C07) fechada via desambiguacao em 2
    cenarios em que o valor era ambiguo:

    - Antes: `NOT_REQUESTED` cobria 3 cenarios distintos: (a) cliente nao
      enviou flag de escalation; (b) cliente enviou flag MAS hard-trigger
      de fallback (provider down / budget exceeded) curto-circuitou antes
      do gate-eval; (c) cliente enviou flag MAS sonnet_factory injetada
      e None (deployment sem Sonnet disponivel).
    - Depois (esta versao): apenas (a) usa NOT_REQUESTED. Os cenarios (b)
      e (c) usam valores especificos abaixo. Observability ganha sinal
      sem custo de migracao - audit metadado registra o valor literal.
    """

    NOT_REQUESTED = "not_requested"
    GRANTED = "granted"
    DENIED_GATE_EVAL_FAILED = "denied_gate_eval_failed"
    DENIED_GATE_EVAL_MISSING = "denied_gate_eval_missing"
    DENIED_FALLBACK_ACTIVE = "denied_fallback_active"
    DENIED_SONNET_UNAVAILABLE = "denied_sonnet_unavailable"


class ProviderUnavailableError(RuntimeError):
    """Raised when Haiku is unavailable and no fallback is permitted."""


class ForcedProviderDeniedError(RuntimeError):
    """Raised when X-Force-Provider is requested by a non-ADMIN_TECNICO role."""


@dataclass(frozen=True, slots=True)
class RouterDecision:
    """Outcome of `LlmRouter.resolve_provider`.

    `provider` is the LlmProvider to call `render_premises` on. `escalation`
    is the canonical reason field forwarded to audit + response payload.
    `fallback_reason` is non-None only when the chosen provider is the stub
    via one of the 3 enumerated hard-triggers.
    """

    provider: LlmProvider
    escalation_requested: bool
    escalation_outcome: EscalationOutcome
    fallback_active: bool
    fallback_reason: FallbackReason | None
    forced_by_admin: bool


class GateEvalCache(Protocol):
    """24h cache of gate-eval results per (prompt_version, intent_kind).

    Implementations MUST return False for unknown (prompt_version, intent_kind)
    tuples (default-deny) so that Sonnet escalation does not slip through when
    no eval evidence exists. AP-LLM-LEAK + AP-13-LLM aligned.
    """

    def is_escalation_allowed(
        self, prompt_version: str, intent_kind: QaIntentKind
    ) -> bool:
        ...


class InMemoryGateEvalCache:
    """In-memory implementation of `GateEvalCache` with TTL 24h.

    Sprint 002 baseline. Production deployment may replace with a Redis-backed
    cache to share state across worker processes. The interface is
    intentionally narrow to make swapping mechanical.
    """

    def __init__(self, ttl_seconds: int = 24 * 60 * 60) -> None:
        self._ttl_seconds = ttl_seconds
        self._entries: dict[tuple[str, QaIntentKind], tuple[bool, float]] = {}

    def is_escalation_allowed(
        self, prompt_version: str, intent_kind: QaIntentKind
    ) -> bool:
        key = (prompt_version, intent_kind)
        entry = self._entries.get(key)
        if entry is None:
            return False
        allowed, expires_at = entry
        if time.monotonic() > expires_at:
            del self._entries[key]
            return False
        return allowed

    def record_eval_result(
        self,
        prompt_version: str,
        intent_kind: QaIntentKind,
        allowed: bool,
    ) -> None:
        self._entries[(prompt_version, intent_kind)] = (
            allowed,
            time.monotonic() + self._ttl_seconds,
        )


@dataclass(slots=True)
class _ProviderHealthWindow:
    """Rolling window of recent failures for the Haiku provider.

    Hard-trigger 1 of NIVEL-0 §2.1: 3 consecutive 5xx/timeout in 60s flips
    the router to the stub-deterministico explicit fallback. The window is
    reset whenever a 2xx response is recorded.
    """

    window_seconds: float = 60.0
    threshold: int = 3
    failures: deque[float] = field(default_factory=deque)
    budget_exceeded_until: float | None = None

    def record_success(self) -> None:
        self.failures.clear()

    def record_failure(self) -> None:
        now = time.monotonic()
        self.failures.append(now)
        cutoff = now - self.window_seconds
        while self.failures and self.failures[0] < cutoff:
            self.failures.popleft()

    def record_budget_exceeded(self, lockout_seconds: float = 3600.0) -> None:
        self.budget_exceeded_until = time.monotonic() + lockout_seconds

    def should_short_circuit(self) -> FallbackReason | None:
        if (
            self.budget_exceeded_until is not None
            and time.monotonic() < self.budget_exceeded_until
        ):
            return FallbackReason.BUDGET_EXCEEDED
        if len(self.failures) >= self.threshold:
            return FallbackReason.PROVIDER_INDISPONIVEL
        return None


class LlmRouter:
    """Single canonical decision point for choosing the LLM provider.

    Wired into qa_orchestrator_service via DI. The router OWNS the no-silent-
    fallback invariant: callers do NOT bypass this router to pick a provider
    directly. Tests in `tests/backend/test_llm_router_no_silent_fallback.py`
    assert the invariant programmatically.
    """

    def __init__(
        self,
        haiku_provider: LlmProvider,
        sonnet_provider_factory: SonnetProviderFactory | None = None,
        stub_provider: StubDeterministicLlmProvider | None = None,
        gate_eval_cache: GateEvalCache | None = None,
        prompt_version: str = PROMPT_VERSION_V020,
    ) -> None:
        self._haiku = haiku_provider
        self._sonnet_factory = sonnet_provider_factory
        self._stub = stub_provider or StubDeterministicLlmProvider()
        self._gate_eval = gate_eval_cache or InMemoryGateEvalCache()
        self._prompt_version = prompt_version
        self._haiku_health = _ProviderHealthWindow()

    def resolve_provider(
        self,
        *,
        intent_kind: QaIntentKind,
        role: InternalRole,
        escalate_header: str | None,
        escalate_body: str | None,
        force_provider_header: str | None,
    ) -> RouterDecision:
        # --- 1. Forced provider (NIVEL-0 hard-trigger 3) ---------------------
        if force_provider_header is not None:
            forced = force_provider_header.strip().lower()
            if forced == "stub-deterministico":
                if role not in {InternalRole.ADMIN_TECNICO}:
                    raise ForcedProviderDeniedError(
                        "X-Force-Provider requires ADMIN_TECNICO role"
                    )
                return RouterDecision(
                    provider=self._stub,
                    escalation_requested=False,
                    escalation_outcome=EscalationOutcome.NOT_REQUESTED,
                    fallback_active=True,
                    fallback_reason=FallbackReason.FORCED_BY_ADMIN,
                    forced_by_admin=True,
                )
            # Any other forced value is silently ignored (no smuggling vector).

        # --- 2. Stub hard-triggers 1+2 (provider down / budget exceeded) -----
        # These short-circuits run BEFORE escalation check because budget /
        # provider down apply globally regardless of Sonnet request.
        fallback_reason = self._haiku_health.should_short_circuit()
        if fallback_reason is not None:
            escalation_requested = self._is_escalation_requested(
                escalate_header, escalate_body
            )
            # NIVEL-4-OBS-2: se cliente havia pedido escalation MAS hard-trigger
            # de fallback disparou, sinalizar `DENIED_FALLBACK_ACTIVE` em vez
            # de `NOT_REQUESTED` (anteriormente ambiguo). Observability ganha
            # sinal para distinguir "cliente nao pediu" de "cliente pediu mas
            # fallback bloqueou antes do gate-eval".
            outcome = (
                EscalationOutcome.DENIED_FALLBACK_ACTIVE
                if escalation_requested
                else EscalationOutcome.NOT_REQUESTED
            )
            return RouterDecision(
                provider=self._stub,
                escalation_requested=escalation_requested,
                escalation_outcome=outcome,
                fallback_active=True,
                fallback_reason=fallback_reason,
                forced_by_admin=False,
            )

        # --- 3. Sonnet escalation (NIVEL-4 strict opt-in + gate-eval) -------
        escalation_requested = self._is_escalation_requested(
            escalate_header, escalate_body
        )
        if escalation_requested:
            if self._sonnet_factory is None:
                # NIVEL-4-OBS-2: deployment Fase 1 sem Sonnet disponivel +
                # cliente pediu escalation. Sinalizar `DENIED_SONNET_UNAVAILABLE`
                # explicitamente em vez de cair em `NOT_REQUESTED` ambiguo.
                # Permanece Haiku - NUNCA silent upgrade.
                return RouterDecision(
                    provider=self._haiku,
                    escalation_requested=True,
                    escalation_outcome=EscalationOutcome.DENIED_SONNET_UNAVAILABLE,
                    fallback_active=False,
                    fallback_reason=None,
                    forced_by_admin=False,
                )
            if self._gate_eval.is_escalation_allowed(
                self._prompt_version, intent_kind
            ):
                sonnet_provider = self._sonnet_factory.build()
                return RouterDecision(
                    provider=sonnet_provider,
                    escalation_requested=True,
                    escalation_outcome=EscalationOutcome.GRANTED,
                    fallback_active=False,
                    fallback_reason=None,
                    forced_by_admin=False,
                )
            # Gate-eval missing OR FAIL -> remain on Haiku (NEVER silently
            # upgrade to Sonnet). Explicit escalation_granted=false signal
            # propagates to audit + response payload.
            return RouterDecision(
                provider=self._haiku,
                escalation_requested=True,
                escalation_outcome=EscalationOutcome.DENIED_GATE_EVAL_MISSING,
                fallback_active=False,
                fallback_reason=None,
                forced_by_admin=False,
            )

        # --- 4. Default branch: Haiku ---------------------------------------
        return RouterDecision(
            provider=self._haiku,
            escalation_requested=escalation_requested,
            escalation_outcome=EscalationOutcome.NOT_REQUESTED,
            fallback_active=False,
            fallback_reason=None,
            forced_by_admin=False,
        )

    def record_haiku_success(self) -> None:
        self._haiku_health.record_success()

    def record_haiku_failure(self) -> None:
        self._haiku_health.record_failure()

    def record_budget_exceeded(self) -> None:
        self._haiku_health.record_budget_exceeded()

    def grant_escalation_for(self, intent_kind: QaIntentKind) -> None:
        """Test/admin helper - records a PASS gate-eval for the given intent.

        Used by `tests/backend/test_llm_router_no_silent_fallback.py` to set
        up the precondition for Sonnet escalation. In production the eval set
        runner records gate-eval results after the Phase 4 validation step.
        """
        if isinstance(self._gate_eval, InMemoryGateEvalCache):
            self._gate_eval.record_eval_result(
                self._prompt_version, intent_kind, True
            )

    @staticmethod
    def _is_escalation_requested(
        escalate_header: str | None, escalate_body: str | None
    ) -> bool:
        header_value = (escalate_header or "").strip().lower()
        body_value = (escalate_body or "").strip().lower()
        return header_value == "sonnet" or body_value == "sonnet"


@dataclass(frozen=True, slots=True, repr=False)
class SonnetProviderFactory:
    """Factory used by the router to build a Sonnet provider on demand.

    Sonnet 4.5 is only instantiated AFTER gate-eval passes (NIVEL-4). The
    factory is configured at DI bootstrap with the API key + client and
    invoked lazily by the router. This keeps the secret + client lifetime
    scoped to the actual Sonnet call.

    AP-12 universal CRITICAL: the dataclass-auto `__repr__` and `__str__` are
    SUPPRESSED (`repr=False`) and replaced by redacted variants below. The
    auto `__repr__` would emit `SonnetProviderFactory(api_key='sk-ant-...')`
    in any `print()`, `logger.debug(factory)`, exception traceback that
    serializes locals, APM payload, or REPL/notebook session - all of which
    are latent secret-leak vectors flagged by TL code-review CO-1 (parecer
    TL §3, handoff `2026-05-22_tech-lead-senior_para_pm-senior_code-review-
    cand-S2-C07.md`). Regression covered by
    `test_sonnet_provider_factory_repr_does_not_leak_api_key` in
    `tests/backend/test_llm_router_no_silent_fallback.py`.
    """

    api_key: str
    client: object | None = None

    def __repr__(self) -> str:
        client_marker = "<set>" if self.client is not None else "None"
        return (
            f"SonnetProviderFactory(api_key=***REDACTED***, client={client_marker})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def build(self) -> AnthropicLlmProvider:
        return AnthropicLlmProvider(
            api_key=self.api_key,
            model=MODEL_SONNET_4_5,
            client=self.client,
        )


__all__ = [
    "EscalationOutcome",
    "ForcedProviderDeniedError",
    "GateEvalCache",
    "InMemoryGateEvalCache",
    "LlmRouter",
    "ProviderUnavailableError",
    "RouterDecision",
    "SonnetProviderFactory",
]

_ = MODEL_HAIKU_4_5
