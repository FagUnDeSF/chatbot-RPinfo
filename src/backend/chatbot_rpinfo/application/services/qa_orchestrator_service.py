"""QA orchestrator service - V5 NIVEL-0 a NIVEL-5 implemented.

Flow per request:

  1. Generate `request_id` (UUID v4).
  2. NIVEL-2 content policy on `question` (prompt injection + jailbreak +
     privilege escalation Security ajuste #3) -> if match: block HTTP 422
     `reason=content_policy_blocked`.
  3. NIVEL-1 §3.1 PII boundary pre-egress on `question` (`assert_no_sensitive
     _identifiers` with RG-SP + Cartao BR Security ajuste #1) -> if match:
     block HTTP 422 `reason=pii_detectado_pre_egress`.
  4. NIVEL-0 §2.2 intent classifier deterministico -> if UNKNOWN: short-
     circuit to negativa honesta `reason=intent_nao_reconhecido` BEFORE any
     LLM call (filters ~95% of adversarial traffic per V5 §9.1).
  5. ERP read-only allowlisted lookup -> if rows==0: short-circuit to
     negativa honesta `reason=dado_indisponivel`.
  6. LlmRouter.resolve_provider (NIVEL-4 anti-fallback-silencioso): choose
     Haiku default OR Sonnet (only with explicit opt-in + gate-eval PASS)
     OR stub-deterministico (only on 3 hard-triggers).
  7. Provider.render_premises -> Anthropic SDK call OR stub local generation.
     Provider returns LlmCallMetadata (17 NIVEL-3 fields).
  8. NIVEL-1 §3.2 PII recall mask over premises -> any PII hits redacted
     in-place with [REDACTED-{kind}] + audit flag.
  9. NIVEL-1 §3.2 citation check -> answered with source=None blocks HTTP 422
     `reason=citation_missing` (out of S001 scope; defensive guard kept).
 10. NIVEL-3 audit: AuditService.record_query_event with full 19-field
     metadata (17 V5 + 3 Security ajustes).

CG-04 absolute: nenhum payload bruto e persistido. AP-12 universal: no API
key value flows through this service.
"""

from __future__ import annotations

import time
from uuid import uuid4

from chatbot_rpinfo.application.services.audit_service import AuditService
from chatbot_rpinfo.application.services.erp_readonly_service import ErpReadonlyService
from chatbot_rpinfo.application.services.intent_classifier import IntentClassifier
from chatbot_rpinfo.application.services.llm_provider import (
    PROMPT_PATH_V020,
    PROMPT_VERSION_V020,
    LlmCallMetadata,
    empty_metadata_for,
)
from chatbot_rpinfo.application.services.llm_router import (
    EscalationOutcome,
    ForcedProviderDeniedError,
    LlmRouter,
    RouterDecision,
)
from chatbot_rpinfo.domain.entities import (
    AuditResponseType,
    AuditSource,
    AuthenticatedPrincipal,
    ErpReadonlyQuery,
    FallbackReason,
    QaAnswer,
    QaAnswerType,
    QaInsufficientReason,
    QaIntent,
    QaIntentKind,
)
from chatbot_rpinfo.domain.policies import (
    ContentPolicyMatch,
    SensitiveDataInTextError,
    SensitiveIdentifierHit,
    assert_no_sensitive_identifiers,
    detect_content_policy_violation,
    redact_sensitive_identifiers,
)

PROMPT_VERSION = PROMPT_VERSION_V020
PROMPT_PATH = PROMPT_PATH_V020
DEFAULT_ERP_LIMIT = 10


class ContentPolicyBlockedError(ValueError):
    """Raised when NIVEL-2 content policy blocks the request."""

    def __init__(self, match: ContentPolicyMatch) -> None:
        super().__init__(f"content_policy_blocked:{match.pattern_id}")
        self.match = match


class PiiBoundaryError(ValueError):
    """Raised when NIVEL-1 PII boundary pre-egress blocks the request."""

    def __init__(self, kind: str) -> None:
        super().__init__(f"pii_detectado_pre_egress:{kind}")
        self.kind = kind


class QaOrchestratorService:
    def __init__(
        self,
        intent_classifier: IntentClassifier,
        erp_readonly_service: ErpReadonlyService,
        llm_router: LlmRouter,
        audit_service: AuditService,
    ) -> None:
        self._intent_classifier = intent_classifier
        self._erp_readonly_service = erp_readonly_service
        self._llm_router = llm_router
        self._audit_service = audit_service

    def ask(  # noqa: PLR0913 - canonical signature aligned with NIVEL-3 V5 §5.1
        self,
        principal: AuthenticatedPrincipal,
        question: str,
        idempotency_key: str,
        *,
        escalate_header: str | None = None,
        force_provider_header: str | None = None,
        correlation_id_upstream: str | None = None,
    ) -> QaAnswer:
        t_request_start = time.monotonic()
        request_id = str(uuid4())
        answer_id = str(uuid4())

        # --- NIVEL-2 content policy (block before any other processing) ----
        content_match = detect_content_policy_violation(question)
        if content_match is not None:
            self._audit_blocked(
                principal=principal,
                intent_kind=QaIntentKind.UNKNOWN,
                idempotency_key=idempotency_key,
                content_policy_match=content_match,
                request_id=request_id,
                correlation_id_upstream=correlation_id_upstream,
                latency_ms=int((time.monotonic() - t_request_start) * 1000),
            )
            raise ContentPolicyBlockedError(content_match)

        # --- NIVEL-1 §3.1 PII boundary pre-egress --------------------------
        try:
            assert_no_sensitive_identifiers(question)
        except SensitiveDataInTextError as exc:
            self._audit_blocked(
                principal=principal,
                intent_kind=QaIntentKind.UNKNOWN,
                idempotency_key=idempotency_key,
                pii_kind=exc.kind,
                request_id=request_id,
                correlation_id_upstream=correlation_id_upstream,
                latency_ms=int((time.monotonic() - t_request_start) * 1000),
            )
            raise PiiBoundaryError(exc.kind) from exc

        # --- NIVEL-0 §2.2 intent classifier deterministico ------------------
        intent = self._intent_classifier.classify(question)
        if intent.kind is QaIntentKind.UNKNOWN:
            metadata = empty_metadata_for(self._llm_router._stub)  # noqa: SLF001
            return self._record_and_build_negative(
                principal=principal,
                answer_id=answer_id,
                intent=intent,
                source=None,
                reason=QaInsufficientReason.INTENT_NAO_RECONHECIDO,
                idempotency_key=idempotency_key,
                metadata=metadata,
                request_id=request_id,
                correlation_id_upstream=correlation_id_upstream,
                latency_total_ms=int((time.monotonic() - t_request_start) * 1000),
            )

        # --- NIVEL-0 §2.3 ERP read-only allowlist ---------------------------
        assert intent.erp_query_name is not None
        erp_query = ErpReadonlyQuery(
            name=intent.erp_query_name,
            parameters={},
            limit=DEFAULT_ERP_LIMIT,
        )
        erp_result = self._erp_readonly_service.execute(
            principal=principal,
            query=erp_query,
            idempotency_key=f"{idempotency_key}-erp",
        )

        # --- NIVEL-4 LlmRouter.resolve_provider -----------------------------
        try:
            decision = self._llm_router.resolve_provider(
                intent_kind=intent.kind,
                role=principal.user.role,
                escalate_header=escalate_header,
                escalate_body=None,
                force_provider_header=force_provider_header,
            )
        except ForcedProviderDeniedError as exc:
            self._audit_blocked(
                principal=principal,
                intent_kind=intent.kind,
                idempotency_key=idempotency_key,
                pii_kind=None,
                request_id=request_id,
                correlation_id_upstream=correlation_id_upstream,
                latency_ms=int((time.monotonic() - t_request_start) * 1000),
                forced_provider_denied=True,
            )
            raise PiiBoundaryError("forced_provider_role_denied") from exc

        if erp_result.row_count == 0:
            metadata = empty_metadata_for(decision.provider)
            return self._record_and_build_negative(
                principal=principal,
                answer_id=answer_id,
                intent=intent,
                source=erp_result.source,
                reason=QaInsufficientReason.DADO_INDISPONIVEL,
                idempotency_key=idempotency_key,
                metadata=metadata,
                decision=decision,
                request_id=request_id,
                correlation_id_upstream=correlation_id_upstream,
                latency_total_ms=int((time.monotonic() - t_request_start) * 1000),
            )

        # --- NIVEL-0 §2.4 Provider call (Haiku / Sonnet / stub) ------------
        try:
            raw_premises = decision.provider.render_premises(intent, erp_result.rows)
            self._llm_router.record_haiku_success()
        except Exception:
            # Categoria especifica LLM CRITICAL: NEVER swap silently to Sonnet
            # on Haiku error. Mark Haiku failure window and return negativa
            # honesta with provider_indisponivel reason; the next request
            # MAY land on stub via NIVEL-0 hard-trigger 1.
            self._llm_router.record_haiku_failure()
            metadata = empty_metadata_for(decision.provider)
            return self._record_and_build_negative(
                principal=principal,
                answer_id=answer_id,
                intent=intent,
                source=erp_result.source,
                reason=QaInsufficientReason.PROVIDER_INDISPONIVEL,
                idempotency_key=idempotency_key,
                metadata=metadata,
                decision=decision,
                request_id=request_id,
                correlation_id_upstream=correlation_id_upstream,
                latency_total_ms=int((time.monotonic() - t_request_start) * 1000),
                fallback_active=True,
                fallback_reason=FallbackReason.PROVIDER_INDISPONIVEL,
            )

        metadata = decision.provider.consume_last_metadata()
        latency_total_ms = int((time.monotonic() - t_request_start) * 1000)

        # --- NIVEL-1 §3.2 PII recall mask over output ----------------------
        masked_premises, all_hits = self._redact_premises(raw_premises)
        pii_redacted = bool(all_hits)
        # CG-04-OBS-1 fechada: `hit.kind` e publicavel (categoria); `hit.matched_value`
        # NUNCA persistido - apenas o conjunto de kinds e propagado para audit.
        categories = tuple(sorted({hit.kind for hit in all_hits}))

        # NIVEL-1 §3.2 citation check (defensive; in S001 caminho positivo
        # always has source non-null because erp_result.source is populated).
        if erp_result.source is None:
            self._audit_blocked(
                principal=principal,
                intent_kind=intent.kind,
                idempotency_key=idempotency_key,
                pii_kind="citation_missing",
                request_id=request_id,
                correlation_id_upstream=correlation_id_upstream,
                latency_ms=latency_total_ms,
            )
            raise PiiBoundaryError("citation_missing")

        self._audit_answered(
            principal=principal,
            intent=intent,
            idempotency_key=idempotency_key,
            metadata=metadata,
            decision=decision,
            pii_redacted=pii_redacted,
            pii_count=len(all_hits),
            pii_categories=categories,
            request_id=request_id,
            correlation_id_upstream=correlation_id_upstream,
            latency_total_ms=latency_total_ms,
        )
        return QaAnswer(
            answer_id=answer_id,
            answer_type=QaAnswerType.ANSWERED,
            intent=intent,
            rows=erp_result.rows,
            source=erp_result.source,
            premises=masked_premises,
            reason=None,
            prompt_version=PROMPT_VERSION,
            provider=decision.provider.name,
            model=decision.provider.model,
            fallback_active=decision.fallback_active,
            fallback_reason=decision.fallback_reason,
            escalation_requested=decision.escalation_requested,
            escalation_granted=decision.escalation_outcome == EscalationOutcome.GRANTED,
            pii_redacted_pos_egress=pii_redacted,
            pii_redacted_categories=categories,
        )

    @staticmethod
    def _redact_premises(
        premises: tuple[str, ...],
    ) -> tuple[tuple[str, ...], tuple[SensitiveIdentifierHit, ...]]:
        masked: list[str] = []
        all_hits: list[SensitiveIdentifierHit] = []
        for premise in premises:
            redacted_text, hits = redact_sensitive_identifiers(premise)
            masked.append(redacted_text)
            all_hits.extend(hits)
        return tuple(masked), tuple(all_hits)

    def _record_and_build_negative(  # noqa: PLR0913 - canonical signature
        self,
        *,
        principal: AuthenticatedPrincipal,
        answer_id: str,
        intent: QaIntent,
        source: str | None,
        reason: QaInsufficientReason,
        idempotency_key: str,
        metadata: LlmCallMetadata,
        decision: RouterDecision | None = None,
        request_id: str,
        correlation_id_upstream: str | None,
        latency_total_ms: int,
        fallback_active: bool = False,
        fallback_reason: FallbackReason | None = None,
    ) -> QaAnswer:
        effective_fallback_active = fallback_active or (
            decision.fallback_active if decision is not None else False
        )
        effective_fallback_reason = fallback_reason or (
            decision.fallback_reason if decision is not None else None
        )
        escalation_requested = decision.escalation_requested if decision else False
        escalation_granted = (
            decision is not None
            and decision.escalation_outcome == EscalationOutcome.GRANTED
        )

        provider_name = decision.provider.name if decision else metadata.provider_used
        provider_model = decision.provider.model if decision else metadata.model_used

        self._audit_service.record_query_event(
            principal=principal,
            intent=f"qa_orchestrator:{intent.kind.value}",
            source=AuditSource.QA_ORCHESTRATOR,
            response_type=AuditResponseType.INSUFFICIENT_DATA,
            insufficient_data=True,
            idempotency_key=f"{idempotency_key}-qa",
            llm_metadata=metadata,
            escalation_requested=escalation_requested,
            escalation_granted=escalation_granted,
            fallback_active=effective_fallback_active,
            fallback_reason=effective_fallback_reason,
            request_id=request_id,
            correlation_id_upstream=correlation_id_upstream,
        )
        _ = latency_total_ms  # forwarded via metadata.latency_ms_total
        return QaAnswer(
            answer_id=answer_id,
            answer_type=QaAnswerType.INSUFFICIENT_DATA,
            intent=intent,
            rows=(),
            source=source,
            premises=(),
            reason=reason,
            prompt_version=PROMPT_VERSION,
            provider=provider_name,
            model=provider_model,
            fallback_active=effective_fallback_active,
            fallback_reason=effective_fallback_reason,
            escalation_requested=escalation_requested,
            escalation_granted=escalation_granted,
        )

    def _audit_answered(  # noqa: PLR0913
        self,
        *,
        principal: AuthenticatedPrincipal,
        intent: QaIntent,
        idempotency_key: str,
        metadata: LlmCallMetadata,
        decision: RouterDecision,
        pii_redacted: bool,
        pii_count: int,
        pii_categories: tuple[str, ...],
        request_id: str,
        correlation_id_upstream: str | None,
        latency_total_ms: int,
    ) -> None:
        self._audit_service.record_query_event(
            principal=principal,
            intent=f"qa_orchestrator:{intent.kind.value}",
            source=AuditSource.QA_ORCHESTRATOR,
            response_type=AuditResponseType.ANSWERED,
            insufficient_data=False,
            idempotency_key=f"{idempotency_key}-qa",
            llm_metadata=metadata,
            escalation_requested=decision.escalation_requested,
            escalation_granted=decision.escalation_outcome == EscalationOutcome.GRANTED,
            pii_redacted_pos_egress=pii_redacted,
            pii_redacted_count=pii_count,
            pii_redacted_categories=pii_categories,
            fallback_active=decision.fallback_active,
            fallback_reason=decision.fallback_reason,
            request_id=request_id,
            correlation_id_upstream=correlation_id_upstream,
        )
        _ = latency_total_ms

    def _audit_blocked(  # noqa: PLR0913
        self,
        *,
        principal: AuthenticatedPrincipal,
        intent_kind: QaIntentKind,
        idempotency_key: str,
        request_id: str,
        correlation_id_upstream: str | None,
        latency_ms: int,
        content_policy_match: ContentPolicyMatch | None = None,
        pii_kind: str | None = None,
        forced_provider_denied: bool = False,
    ) -> None:
        # Audit pre-LLM blocks. The intent recorded is the raw classifier
        # value (`qa_orchestrator:<kind>`); for blocked requests we use the
        # bucket `qa_orchestrator:blocked` to distinguish blocked traffic
        # from unknown-intent negativa honesta in dashboards.
        intent_label = "qa_orchestrator:blocked"
        if content_policy_match is None and pii_kind is None and not forced_provider_denied:
            intent_label = f"qa_orchestrator:{intent_kind.value}"
        self._audit_service.record_query_event(
            principal=principal,
            intent=intent_label,
            source=AuditSource.QA_ORCHESTRATOR,
            response_type=AuditResponseType.FORBIDDEN
            if forced_provider_denied
            else AuditResponseType.ERROR,
            insufficient_data=True,
            idempotency_key=f"{idempotency_key}-qa-blocked",
            content_policy_blocked=content_policy_match is not None,
            content_policy_pattern_id=(
                content_policy_match.pattern_id if content_policy_match else None
            ),
            pii_detectado_pre_egress=pii_kind is not None and pii_kind != "citation_missing",
            request_id=request_id,
            correlation_id_upstream=correlation_id_upstream,
        )
        _ = latency_ms
