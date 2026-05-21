from __future__ import annotations

from chatbot_rpinfo.application.services.audit_service import AuditService
from chatbot_rpinfo.config import AppSettings
from chatbot_rpinfo.domain.entities import (
    AuditResponseType,
    AuditSource,
    AuthenticatedPrincipal,
    ErpReadonlyQuery,
    ErpReadonlyResult,
)
from chatbot_rpinfo.domain.repositories import ErpReadonlyRepository


class ErpReadonlyError(Exception):
    pass


class ErpReadonlyQueryNotAllowedError(ErpReadonlyError):
    pass


class ErpReadonlyLimitError(ErpReadonlyError):
    pass


class ErpReadonlyService:
    def __init__(
        self,
        settings: AppSettings,
        repository: ErpReadonlyRepository,
        audit_service: AuditService,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._audit_service = audit_service

    def execute(
        self,
        principal: AuthenticatedPrincipal,
        query: ErpReadonlyQuery,
        idempotency_key: str,
    ) -> ErpReadonlyResult:
        if query.limit > self._settings.erp_readonly_max_rows:
            raise ErpReadonlyLimitError("limit_exceeds_configured_max_rows")
        if not self._repository.is_allowed(query.name):
            raise ErpReadonlyQueryNotAllowedError("query_not_allowlisted")

        result = self._repository.execute(query)
        self._audit_service.record_query_event(
            principal=principal,
            intent=f"erp_readonly:{query.name}",
            source=AuditSource.ERP_READONLY,
            response_type=AuditResponseType.ANSWERED
            if result.row_count > 0
            else AuditResponseType.INSUFFICIENT_DATA,
            insufficient_data=result.row_count == 0,
            idempotency_key=idempotency_key,
        )
        return result
