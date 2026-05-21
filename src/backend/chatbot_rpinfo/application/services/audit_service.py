from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from chatbot_rpinfo.domain.entities import (
    AuditEvent,
    AuditResponseType,
    AuditSource,
    AuthenticatedPrincipal,
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
    ) -> AuditEvent:
        if not self._can_record_source(principal.user.role, source):
            raise AuditAuthorizationError("role_cannot_record_source")

        assert_no_sensitive_identifiers(intent)

        event = AuditEvent(
            event_id=str(uuid4()),
            username=principal.user.username,
            role=principal.user.role,
            occurred_at=datetime.now(UTC),
            intent=intent,
            source=source,
            response_type=response_type,
            insufficient_data=insufficient_data,
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
            }
        if role is InternalRole.PREVENCAO:
            return source in {AuditSource.ERP_READONLY, AuditSource.PREVENCAO}
        return False
