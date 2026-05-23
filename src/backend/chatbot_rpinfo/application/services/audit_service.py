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

    def record_query_event(
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
        rate_limit_hit: bool = False,
        rate_limit_window_seconds: int = 0,
        role_used: str | None = None,
    ) -> AuditEvent:
        return self._record_event(
            principal=principal,
            intent=intent,
            source=source,
            response_type=response_type,
            insufficient_data=insufficient_data,
            idempotency_key=idempotency_key,
            authorize_source=True,
            llm_metadata=llm_metadata,
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
            rate_limit_hit=rate_limit_hit,
            rate_limit_window_seconds=rate_limit_window_seconds,
            role_used=role_used,
        )

    def record_rate_limit_hit(
        self,
        *,
        principal: AuthenticatedPrincipal,
        idempotency_key: str,
        window_seconds: int,
    ) -> AuditEvent:
        return self._record_event(
            principal=principal,
            intent="rate limit exceeded",
            source=AuditSource.SISTEMA,
            response_type=AuditResponseType.ERROR,
            insufficient_data=False,
            idempotency_key=idempotency_key,
            authorize_source=False,
            rate_limit_hit=True,
            rate_limit_window_seconds=window_seconds,
            role_used=principal.user.role.value,
        )

    def _record_event(
        self,
        principal: AuthenticatedPrincipal,
        intent: str,
        source: AuditSource,
        response_type: AuditResponseType,
        insufficient_data: bool,
        idempotency_key: str,
        *,
        authorize_source: bool,
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
        rate_limit_hit: bool = False,
        rate_limit_window_seconds: int = 0,
        role_used: str | None = None,
    ) -> AuditEvent:
        if authorize_source and not self._can_record_source(principal.user.role, source):
            raise AuditAuthorizationError("role_cannot_record_source")

        assert_no_sensitive_identifiers(intent)
        if correlation_id_upstream is not None:
            assert_no_sensitive_identifiers(correlation_id_upstream)

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
            rate_limit_hit=rate_limit_hit,
            rate_limit_window_seconds=rate_limit_window_seconds,
            role_used=role_used,
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
