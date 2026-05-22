"""Anti-fallback-silencioso programmatic asserts (AP-2 LLM CRITICAL).

These tests are the gate-of-promotion canonical asserts for NIVEL-4 V5 §6.
They cover the 3 hard rules in `application/services/llm_router.py`:

  1. Haiku NEVER silently falls back to Sonnet (error in Haiku does NOT
     swap to Sonnet).
  2. Sonnet escalation is only granted with explicit opt-in flag AND
     gate-eval PASS within 24h.
  3. Stub fallback is signalled explicitly in the response payload + header
     (4 elements of anti-fallback-silencioso satisfied).
"""

from __future__ import annotations

from typing import Any

import pytest

from chatbot_rpinfo.application.services.llm_provider import (
    MODEL_HAIKU_4_5,
    PROMPT_VERSION_V020,
    LlmCallMetadata,
    StubDeterministicLlmProvider,
)
from chatbot_rpinfo.application.services.llm_router import (
    EscalationOutcome,
    ForcedProviderDeniedError,
    InMemoryGateEvalCache,
    LlmRouter,
    SonnetProviderFactory,
)
from chatbot_rpinfo.domain.entities import (
    ErpRow,
    FallbackReason,
    InternalRole,
    QaIntent,
    QaIntentKind,
)


class _FakeHaikuProvider:
    """Test double that mimics AnthropicLlmProvider without hitting the SDK."""

    def __init__(self, *, model: str = MODEL_HAIKU_4_5, fail: bool = False) -> None:
        self._model = model
        self._fail = fail
        self._last_metadata: LlmCallMetadata | None = None

    @property
    def name(self) -> str:
        return "anthropic-haiku-4-5" if self._model == MODEL_HAIKU_4_5 else "anthropic-sonnet-4-5"

    @property
    def model(self) -> str | None:
        return self._model

    def render_premises(
        self, intent: QaIntent, rows: tuple[ErpRow, ...]
    ) -> tuple[str, ...]:
        if self._fail:
            raise RuntimeError("provider_5xx_simulated")
        self._last_metadata = LlmCallMetadata(
            provider_used=self.name,
            model_used=self._model,
            prompt_version=PROMPT_VERSION_V020,
            cache_hit=True,
            cache_read_tokens=350,
            input_tokens_total=200,
            output_tokens_total=80,
            latency_ms_total=900,
        )
        return ("fake premise",)

    def consume_last_metadata(self) -> LlmCallMetadata:
        if self._last_metadata is None:
            return LlmCallMetadata(
                provider_used=self.name,
                model_used=self._model,
                prompt_version=PROMPT_VERSION_V020,
            )
        metadata = self._last_metadata
        self._last_metadata = None
        return metadata


class _FakeSonnetFactory:
    """Test factory that asserts the router only builds Sonnet when gate-eval PASS."""

    def __init__(self) -> None:
        self.build_count = 0

    def build(self) -> Any:
        self.build_count += 1
        return _FakeHaikuProvider(model="claude-sonnet-4-5-20250929")


def _make_router(
    *,
    haiku_fail: bool = False,
    sonnet_factory: Any | None = None,
    gate_eval: InMemoryGateEvalCache | None = None,
) -> tuple[LlmRouter, _FakeHaikuProvider, _FakeSonnetFactory | None]:
    haiku = _FakeHaikuProvider(fail=haiku_fail)
    stub = StubDeterministicLlmProvider()
    factory = sonnet_factory
    router = LlmRouter(
        haiku_provider=haiku,
        sonnet_provider_factory=factory,
        stub_provider=stub,
        gate_eval_cache=gate_eval or InMemoryGateEvalCache(),
    )
    return router, haiku, factory if isinstance(factory, _FakeSonnetFactory) else None


def test_haiku_nao_faz_fallback_silencioso_para_sonnet() -> None:
    """Erro Haiku NUNCA dispara troca silenciosa para Sonnet.

    Cenario: request SEM header `X-LLM-Escalate`. Mesmo se o Haiku falhar
    repetidamente, a rota canonica e fallback EXPLICITO para stub (com sinal
    no payload + header). Sonnet NUNCA e construido.
    """
    factory = _FakeSonnetFactory()
    router, _, _ = _make_router(sonnet_factory=factory)

    # Simulate 3 consecutive Haiku failures (NIVEL-0 hard-trigger 1).
    router.record_haiku_failure()
    router.record_haiku_failure()
    router.record_haiku_failure()

    decision = router.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.PREVENCAO,
        escalate_header=None,
        escalate_body=None,
        force_provider_header=None,
    )

    assert decision.provider.name == "stub-deterministico"
    assert decision.fallback_active is True
    assert decision.fallback_reason is FallbackReason.PROVIDER_INDISPONIVEL
    assert decision.escalation_outcome is EscalationOutcome.NOT_REQUESTED
    # Sonnet factory MUST NOT have been built during fallback path.
    assert factory.build_count == 0


def test_sonnet_so_ativa_com_flag_explicita_e_gate_eval() -> None:
    """Sonnet escalation requires BOTH explicit opt-in flag AND gate-eval PASS.

    Cenarios cobertos:
      (a) Sem flag: permanece Haiku independente de gate-eval.
      (b) Com flag mas gate-eval ausente: permanece Haiku, `escalation_granted=false`.
      (c) Com flag + gate-eval PASS: roteia para Sonnet, `escalation_granted=true`.
    """
    gate = InMemoryGateEvalCache()
    factory = _FakeSonnetFactory()
    router, haiku, _ = _make_router(sonnet_factory=factory, gate_eval=gate)

    # (a) Sem flag -> Haiku.
    decision_a = router.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.PREVENCAO,
        escalate_header=None,
        escalate_body=None,
        force_provider_header=None,
    )
    assert decision_a.provider is haiku
    assert decision_a.escalation_requested is False
    assert decision_a.escalation_outcome is EscalationOutcome.NOT_REQUESTED
    assert factory.build_count == 0

    # (b) Com flag, gate-eval ausente -> Haiku + escalation_denied.
    decision_b = router.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.PREVENCAO,
        escalate_header="sonnet",
        escalate_body=None,
        force_provider_header=None,
    )
    assert decision_b.provider is haiku
    assert decision_b.escalation_requested is True
    assert decision_b.escalation_outcome is EscalationOutcome.DENIED_GATE_EVAL_MISSING
    assert factory.build_count == 0

    # (c) Com flag + gate-eval PASS -> Sonnet granted.
    router.grant_escalation_for(QaIntentKind.INVENTORY_RISK)
    decision_c = router.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.PREVENCAO,
        escalate_header="sonnet",
        escalate_body=None,
        force_provider_header=None,
    )
    assert decision_c.provider.name == "anthropic-sonnet-4-5"
    assert decision_c.escalation_requested is True
    assert decision_c.escalation_outcome is EscalationOutcome.GRANTED
    assert factory.build_count == 1


def test_stub_fallback_propaga_no_response_payload() -> None:
    """Fallback para stub e SEMPRE sinalizado explicitamente.

    Verifica 3 das 4 elementos do anti-fallback-silencioso V5 §6.1.2 que
    cabem no escopo deste teste unit:

    (a) Fallback Matrix - reason enumerated no RouterDecision.
    (b) Log - fallback_active=true + fallback_reason no decision.
    (c) Response payload signal - decision propaga fallback_active.
    Elemento (d) (alerta agendado em monitorar-custo-llm) e testado em
    S2-C08 observabilidade.

    Tambem cobre o hard-trigger 3 (X-Force-Provider com RBAC) e o gate
    de RBAC (ForcedProviderDeniedError quando role nao e ADMIN_TECNICO).
    """
    router, _, _ = _make_router()

    # (a) Hard-trigger 3 (forced by admin) com role ADMIN_TECNICO ok.
    decision = router.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.ADMIN_TECNICO,
        escalate_header=None,
        escalate_body=None,
        force_provider_header="stub-deterministico",
    )
    assert decision.provider.name == "stub-deterministico"
    assert decision.fallback_active is True
    assert decision.fallback_reason is FallbackReason.FORCED_BY_ADMIN
    assert decision.forced_by_admin is True

    # (b) Hard-trigger 3 com role NAO-ADMIN -> recusa explicita.
    with pytest.raises(ForcedProviderDeniedError):
        router.resolve_provider(
            intent_kind=QaIntentKind.INVENTORY_RISK,
            role=InternalRole.COMERCIAL,
            escalate_header=None,
            escalate_body=None,
            force_provider_header="stub-deterministico",
        )

    # (c) Hard-trigger 2 (budget exceeded) -> stub com fallback_reason BUDGET_EXCEEDED.
    router2, _, _ = _make_router()
    router2.record_budget_exceeded()
    decision2 = router2.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.PREVENCAO,
        escalate_header=None,
        escalate_body=None,
        force_provider_header=None,
    )
    assert decision2.provider.name == "stub-deterministico"
    assert decision2.fallback_active is True
    assert decision2.fallback_reason is FallbackReason.BUDGET_EXCEEDED


def test_router_factory_not_buildable_when_sonnet_factory_is_none() -> None:
    """Sem SonnetProviderFactory injetada, escalation com flag continua negada.

    Cenario: deployment Fase 1 onde Direcao optou por NAO disponibilizar
    Sonnet (somente Haiku). Mesmo com header de opt-in valido, router
    permanece em Haiku e marca escalation_granted=false.

    NIVEL-4-OBS-2 (TL §2 parecer S2-C07) fechada: o outcome neste cenario
    e `DENIED_SONNET_UNAVAILABLE` (antes era ambiguo `NOT_REQUESTED`).
    """
    router, haiku, _ = _make_router(sonnet_factory=None)
    router.grant_escalation_for(QaIntentKind.INVENTORY_RISK)

    decision = router.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.DIRECAO,
        escalate_header="sonnet",
        escalate_body=None,
        force_provider_header=None,
    )

    assert decision.provider is haiku
    assert decision.escalation_requested is True
    assert decision.escalation_outcome is EscalationOutcome.DENIED_SONNET_UNAVAILABLE


def test_escalation_outcome_desambiguacao_fallback_ativo_vs_not_requested() -> None:
    """NIVEL-4-OBS-2 (TL §2 parecer S2-C07) - desambiguacao cenarios fallback.

    Antes do fix: `EscalationOutcome.NOT_REQUESTED` era retornado em 3
    cenarios distintos, mascarando o sinal observability. Agora:

    - (a) Cliente NAO pediu escalation + fallback ativo -> `NOT_REQUESTED`
      (sinal correto: nada foi pedido).
    - (b) Cliente PEDIU escalation + fallback ativo (hard-trigger budget
      OR provider down disparou antes do gate-eval) -> `DENIED_FALLBACK_ACTIVE`
      (sinal novo: foi pedido mas bloqueado por motivo distinto de
      gate-eval).
    - (c) Cliente PEDIU escalation + sonnet_factory ausente -> `DENIED_SONNET_UNAVAILABLE`
      (cenario coberto em `test_router_factory_not_buildable_when_sonnet_factory_is_none`).
    """
    factory = _FakeSonnetFactory()

    # (a) Sem flag + fallback ativo -> NOT_REQUESTED.
    router_a, _, _ = _make_router(sonnet_factory=factory)
    router_a.record_budget_exceeded()
    decision_a = router_a.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.PREVENCAO,
        escalate_header=None,
        escalate_body=None,
        force_provider_header=None,
    )
    assert decision_a.provider.name == "stub-deterministico"
    assert decision_a.fallback_active is True
    assert decision_a.escalation_requested is False
    assert decision_a.escalation_outcome is EscalationOutcome.NOT_REQUESTED

    # (b) Com flag + fallback ativo -> DENIED_FALLBACK_ACTIVE (NOVO).
    router_b, _, _ = _make_router(sonnet_factory=factory)
    router_b.record_budget_exceeded()
    decision_b = router_b.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.PREVENCAO,
        escalate_header="sonnet",
        escalate_body=None,
        force_provider_header=None,
    )
    assert decision_b.provider.name == "stub-deterministico"
    assert decision_b.fallback_active is True
    assert decision_b.fallback_reason is FallbackReason.BUDGET_EXCEEDED
    assert decision_b.escalation_requested is True
    assert decision_b.escalation_outcome is EscalationOutcome.DENIED_FALLBACK_ACTIVE
    # Sonnet factory NUNCA chamado em fallback path - hard-trigger curto-circuita.
    assert factory.build_count == 0

    # (c) Mesmo cenario com fallback = provider_indisponivel (3 falhas).
    router_c, _, _ = _make_router(sonnet_factory=factory)
    router_c.record_haiku_failure()
    router_c.record_haiku_failure()
    router_c.record_haiku_failure()
    decision_c = router_c.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.PREVENCAO,
        escalate_header="sonnet",
        escalate_body=None,
        force_provider_header=None,
    )
    assert decision_c.escalation_outcome is EscalationOutcome.DENIED_FALLBACK_ACTIVE
    assert decision_c.fallback_reason is FallbackReason.PROVIDER_INDISPONIVEL


def test_force_provider_com_valor_invalido_e_silenciosamente_ignorado() -> None:
    """NIVEL-4-OBS-1 (TL §2 parecer S2-C07) - cobertura do path "silently
    ignored" em LlmRouter.resolve_provider quando o header X-Force-Provider
    chega com valor != "stub-deterministico".

    Comportamento canonico (llm_router.py:linha "Any other forced value is
    silently ignored (no smuggling vector)"):

      - `X-Force-Provider: stub-deterministico` + role ADMIN_TECNICO -> stub.
      - `X-Force-Provider: stub-deterministico` + role NAO-ADMIN -> recusa.
      - `X-Force-Provider: <qualquer-outra-string>` -> IGNORADO; fluxo segue
        para os hard-triggers / Sonnet / Haiku default.

    Vetor de smuggling protegido: cliente malicioso tenta `X-Force-Provider:
    anthropic-sonnet-4-5` esperando forcar Sonnet sem flag de escalation +
    sem gate-eval. Resultado esperado: Haiku default (NUNCA Sonnet),
    `escalation_outcome=NOT_REQUESTED`, `fallback_active=False`.
    """
    factory = _FakeSonnetFactory()
    router, haiku, _ = _make_router(sonnet_factory=factory)

    # (a) Tentativa de smuggling para Sonnet via X-Force-Provider invalido.
    decision_smuggle_sonnet = router.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.PREVENCAO,
        escalate_header=None,
        escalate_body=None,
        force_provider_header="anthropic-sonnet-4-5",
    )

    assert decision_smuggle_sonnet.provider is haiku
    assert decision_smuggle_sonnet.escalation_requested is False
    assert decision_smuggle_sonnet.escalation_outcome is EscalationOutcome.NOT_REQUESTED
    assert decision_smuggle_sonnet.fallback_active is False
    assert decision_smuggle_sonnet.forced_by_admin is False
    assert factory.build_count == 0  # Sonnet NUNCA construido

    # (b) Valor sintaticamente proximo ("stub-determinist1co" com erro) -> Haiku.
    decision_typo = router.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.ADMIN_TECNICO,
        escalate_header=None,
        escalate_body=None,
        force_provider_header="stub-determinist1co",  # typo proposital
    )
    assert decision_typo.provider is haiku
    assert decision_typo.fallback_active is False
    assert decision_typo.forced_by_admin is False

    # (c) String vazia/whitespace -> Haiku.
    decision_empty = router.resolve_provider(
        intent_kind=QaIntentKind.INVENTORY_RISK,
        role=InternalRole.ADMIN_TECNICO,
        escalate_header=None,
        escalate_body=None,
        force_provider_header="   ",
    )
    assert decision_empty.provider is haiku
    assert decision_empty.fallback_active is False


def test_sonnet_provider_factory_repr_does_not_leak_api_key() -> None:
    """AP-12 universal CRITICAL - SonnetProviderFactory __repr__/__str__ MUST
    redact the api_key field.

    Regression test for TL code-review CO-1 (parecer
    `equipe/tech-lead-senior/code-reviews/2026-05-22_S2-C07_review.md` §3 +
    handoff `2026-05-22_tech-lead-senior_para_pm-senior_code-review-cand-
    S2-C07.md` Foco 3). Before the fix, the dataclass-auto `__repr__` of
    `SonnetProviderFactory(@dataclass frozen=True slots=True)` emitted
    `SonnetProviderFactory(api_key='sk-ant-...', client=None)` in every
    `print()`, `logger.debug(factory)`, exception traceback that serialized
    locals, APM payload, and REPL/notebook session - a latent secret-leak
    vector.

    The fix declares `repr=False` on the dataclass decorator and replaces
    `__repr__` / `__str__` with redacted variants that emit
    `api_key=***REDACTED***`. The literal sentinel below would match a real
    Anthropic key shape but is salted with `LEAK-SENTINEL-DO-NOT-LOG` so that
    if it ever appears in any log/repo/audit a grep flags it immediately as
    a test artifact (not a real leak).
    """
    sentinel = "sk-ant-api03-LEAK-SENTINEL-DO-NOT-LOG"

    factory = SonnetProviderFactory(api_key=sentinel)

    assert sentinel not in repr(factory)
    assert sentinel not in str(factory)
    assert sentinel not in f"{factory!r}"
    assert sentinel not in f"{factory}"
    assert sentinel not in format(factory)
    assert "***REDACTED***" in repr(factory) or "SecretStr" in repr(factory)

    # Defesa em profundidade: factory com client setado tambem nao pode vazar
    # api_key na representacao, e deve sinalizar `<set>` (sem expor o client).
    factory_with_client = SonnetProviderFactory(api_key=sentinel, client=object())
    assert sentinel not in repr(factory_with_client)
    assert "<set>" in repr(factory_with_client)


def test_router_does_not_swap_haiku_for_sonnet_when_haiku_succeeds() -> None:
    """Sucesso de Haiku NUNCA dispara escalation oportunista para Sonnet.

    Trivial-mas-canonical: assert que Haiku saudavel + sem header de
    escalation = Haiku no decision, sempre. Cobre a invariante de
    'silent upgrade'.
    """
    factory = _FakeSonnetFactory()
    sonnet_gate = InMemoryGateEvalCache()
    sonnet_gate.record_eval_result(PROMPT_VERSION_V020, QaIntentKind.SALES_SUMMARY, True)
    router, haiku, _ = _make_router(sonnet_factory=factory, gate_eval=sonnet_gate)

    # Gate-eval PASS para sales_summary, mas request NAO traz flag.
    decision = router.resolve_provider(
        intent_kind=QaIntentKind.SALES_SUMMARY,
        role=InternalRole.COMERCIAL,
        escalate_header=None,
        escalate_body=None,
        force_provider_header=None,
    )

    assert decision.provider is haiku
    assert decision.escalation_requested is False
    assert factory.build_count == 0
