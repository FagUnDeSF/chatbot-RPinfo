from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from chatbot_rpinfo.application.services import (
    ErpReadonlyLimitError,
    ErpReadonlyQueryNotAllowedError,
    ErpReadonlyService,
)
from chatbot_rpinfo.domain.entities import AuthenticatedPrincipal
from chatbot_rpinfo.presentation.dependencies import get_current_principal, get_erp_readonly_service
from chatbot_rpinfo.presentation.dtos import ErpReadonlyQueryRequest, ErpReadonlyQueryResponse

router = APIRouter(prefix="/erp-readonly", tags=["erp-readonly"])


@router.post(
    "/query",
    response_model=ErpReadonlyQueryResponse,
    summary="Execute allowlisted ERP readonly query",
)
def execute_query(
    payload: ErpReadonlyQueryRequest,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[ErpReadonlyService, Depends(get_erp_readonly_service)],
) -> ErpReadonlyQueryResponse:
    try:
        result = service.execute(
            principal=principal,
            query=payload.to_domain(),
            idempotency_key=idempotency_key,
        )
    except ErpReadonlyLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit_exceeds_configured_max_rows",
        ) from exc
    except ErpReadonlyQueryNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="query_not_allowlisted",
        ) from exc
    return ErpReadonlyQueryResponse.from_domain(result)
