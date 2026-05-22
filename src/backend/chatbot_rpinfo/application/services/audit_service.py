from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from chatbot_rpinfo.application.services.llm_provider import LlmCallMetadata
from chatbot_rpinfo.domain.entities import (
    AuditEvent,
    AuditResponseType,
    AuditSource,
    AuthenticatedPrincipal,
    FallbackReason,
    InternalRole,
)
from chatbot_rpinfo.domain.policies import assert_no_sensitive_identifiers
from chatbot_rpinfo.domain.repositories import AuditEventRepository


class AuditAuthorizationError(Exception):
    """Raised when an authenticated role cannot record metadata for a source."""


class AuditService:
    def __init__(self, audit_event_repository: AuditEventRepository) -> None:
        self._audit_event_repository = audit_event_repository

    def record_query_event(  # noqa: PLR0913 - canonical signature mirrors NIVEL-3 V5 §5.1
        self,
        principal: AuthenticatedPrincipal,
        intent: str,
        source: AuditSource,
        response_type: AuditResponseType,
        insufficient_data: bool,
        idempotency_key: str,
        *,
        llm_metadata: LlmCallMetadata | None = None,
        escalation_requested: bool = False,
        escalation_granted: bool = False,
        pii_detectado_pre_egress: bool = False,
        pii_redacted_pos_egress: bool = False,
        pii_redacted_count: int = 0,
        pii_redacted_categories: tuple[str, ...] = (),
        content_policy_blocked: bool = False,
        content_policy_pattern_id: str | None = None,
        refusal_evasion_attempted: bool = False,
        fallback_active: bool = False,
        fallback_reason: FallbackReason | None = None,
        request_id: str | None = None,
        correlation_id_upstream: str | None = None,
    ) -> AuditEvent:
        if not self._can_record_source(principal.user.role, source):
            raise AuditAuthorizationError("role_cannot_record_source")

        assert_no_sensitive_identifiers(intent)
        # CG-04-OBS-2 (TL §2 parecer S2-C07) - defense-in-depth: o header
        # `X-Correlation-Id` chega do upstream sem validacao previa, entao
        # validar antes de persistir no audit evita que CPF/CNPJ/etc vazem
        # via correlation_id se cliente malicioso injetar PII no header.
        # `request_id` e UUID v4 gerado pelo controller (deterministicamente
        # seguro), portanto NAO precisa validacao.
        if correlation_id_upstream is not None:
            assert_no_sensitive_identifiers(correlation_id_upstream)

        # Default LLM-metadata fields when caller did not pass a metadata
        # struct (S001 stub-deterministico path or NIVEL-2 content-policy
        # bloqueio pre-LLM that never reached the provider).
        provider_used: str | None = None
        model_used: str | None = None
        prompt_version: str | None = None
        cache_hit = False
        cache_read_tokens = 0
        cache_write_tokens = 0
        input_tokens_total = 0
        output_tokens_total = 0
        cost_usd: Decimal | None = None
        latency_ms_total = 0
        latency_ms_provider_call = 0
        if llm_metadata is not None:
            provider_used = llm_metadata.provider_used
            model_used = llm_metadata.model_used
            prompt_version = llm_metadata.prompt_version
            cache_hit = llm_metadata.cache_hit
            cache_read_tokens = llm_metadata.cache_read_tokens
            cache_write_tokens = llm_metadata.cache_write_tokens
            input_tokens_total = llm_metadata.input_tokens_total
            output_tokens_total = llm_metadata.output_tokens_total
            cost_usd = llm_metadata.cost_usd
            latency_ms_total = llm_metadata.latency_ms_total
            latency_ms_provider_call = llm_metadata.latency_ms_provider_call

        event = AuditEvent(
            event_id=str(uuid4()),
            username=principal.user.username,
            role=principal.user.role,
            occurred_at=datetime.now(UTC),
            intent=intent,
            source=source,
            response_type=response_type,
            insufficient_data=insufficient_data,
            provider_used=provider_used,
            model_used=model_used,
            prompt_version=prompt_version,
            cache_hit=cache_hit,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
            input_tokens_total=input_tokens_total,
            output_tokens_total=output_tokens_total,
            cost_usd=cost_usd,
            latency_ms_total=latency_ms_total,
            latency_ms_provider_call=latency_ms_provider_call,
            escalation_requested=escalation_requested,
            escalation_granted=escalation_granted,
            pii_detectado_pre_egress=pii_detectado_pre_egress,
            pii_redacted_pos_egress=pii_redacted_pos_egress,
            pii_redacted_count=pii_redacted_count,
            pii_redacted_categories=pii_redacted_categories,
            content_policy_blocked=content_policy_blocked,
            content_policy_pattern_id=content_policy_pattern_id,
            refusal_evasion_attempted=refusal_evasion_attempted,
            fallback_active=fallback_active,
            fallback_reason=fallback_reason,
            request_id=request_id,
            correlation_id_upstream=correlation_id_upstream,
        )
        return self._audit_event_repository.save_once(idempotency_key, event)

    def list_events(self) -> tuple[AuditEvent, ...]:
        return self._audit_event_repository.list_events()

    @staticmethod
    def _can_record_source(role: InternalRole, source: AuditSource) -> bool:
        if role in {InternalRole.DIRECAO, InternalRole.ADMIN_TECNICO}:
            return True
        if role is InternalRole.COMERCIAL:
            return source in {
                AuditSource.ERP_READONLY,
                AuditSource.VENDAS,
                AuditSource.ESTOQUE,
                AuditSource.QA_ORCHESTRATOR,
            }
        if role is InternalRole.PREVENCAO:
            return source in {
                AuditSource.ERP_READONLY,
                AuditSource.PREVENCAO,
                AuditSource.QA_ORCHESTRATOR,
            }
        return False
