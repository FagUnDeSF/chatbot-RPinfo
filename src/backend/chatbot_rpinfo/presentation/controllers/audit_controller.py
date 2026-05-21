from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from chatbot_rpinfo.application.services import AuditAuthorizationError, AuditService
from chatbot_rpinfo.domain.entities import AuthenticatedPrincipal
from chatbot_rpinfo.presentation.dependencies import get_audit_service, get_current_principal
from chatbot_rpinfo.presentation.dtos import AuditEventResponse, AuditQueryEventRequest

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post(
    "/query-events",
    response_model=AuditEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record query audit metadata",
)
def record_query_event(
    payload: AuditQueryEventRequest,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[AuditService, Depends(get_audit_service)],
) -> AuditEventResponse:
    try:
        event = service.record_query_event(
            principal=principal,
            intent=payload.intent,
            source=payload.source,
            response_type=payload.response_type,
            insufficient_data=payload.insufficient_data,
            idempotency_key=idempotency_key,
        )
    except AuditAuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="role_cannot_record_source",
        ) from exc
    return AuditEventResponse.from_domain(event)
