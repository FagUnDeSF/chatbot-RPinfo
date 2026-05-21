from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from chatbot_rpinfo.application.services import AuthenticationError, InternalAuthService
from chatbot_rpinfo.domain.entities import AuthenticatedPrincipal
from chatbot_rpinfo.presentation.dependencies import (
    get_current_principal,
    get_internal_auth_service,
)
from chatbot_rpinfo.presentation.dtos import InternalLoginRequest, InternalUserResponse

router = APIRouter(prefix="/auth/internal", tags=["auth"])


@router.post("/login", response_model=InternalUserResponse, summary="Internal login")
def login(
    payload: InternalLoginRequest,
    service: Annotated[InternalAuthService, Depends(get_internal_auth_service)],
) -> InternalUserResponse:
    try:
        principal = service.authenticate(
            username=payload.username,
            token=payload.access_token.get_secret_value(),
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_internal_credentials",
        ) from exc
    return InternalUserResponse.from_principal(principal)


@router.get("/me", response_model=InternalUserResponse, summary="Current internal user")
def current_user(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> InternalUserResponse:
    return InternalUserResponse.from_principal(principal)
