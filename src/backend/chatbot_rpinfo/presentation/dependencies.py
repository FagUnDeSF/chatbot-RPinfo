from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from typing import Annotated, cast

from fastapi import Depends, Header, HTTPException, Request, status

from chatbot_rpinfo.application.services import (
    AuditService,
    AuthenticationError,
    HealthService,
    InternalAuthService,
)
from chatbot_rpinfo.config import AppSettings, load_settings
from chatbot_rpinfo.domain.entities import AuthenticatedPrincipal
from chatbot_rpinfo.domain.repositories import AuditEventRepository, InternalUserRepository


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return load_settings()


def get_health_service(settings: Annotated[AppSettings, Depends(get_settings)]) -> HealthService:
    return HealthService(settings=settings)


def get_internal_user_repository(request: Request) -> InternalUserRepository:
    return cast(InternalUserRepository, request.app.state.internal_user_repository)


def get_audit_event_repository(request: Request) -> AuditEventRepository:
    return cast(AuditEventRepository, request.app.state.audit_event_repository)


def get_token_source(request: Request) -> Mapping[str, str]:
    return cast(Mapping[str, str], request.app.state.token_source)


def get_internal_auth_service(
    user_repository: Annotated[InternalUserRepository, Depends(get_internal_user_repository)],
    token_source: Annotated[Mapping[str, str], Depends(get_token_source)],
) -> InternalAuthService:
    return InternalAuthService(user_repository=user_repository, token_source=token_source)


def get_audit_service(
    audit_event_repository: Annotated[AuditEventRepository, Depends(get_audit_event_repository)],
) -> AuditService:
    return AuditService(audit_event_repository=audit_event_repository)


def get_current_principal(
    username: Annotated[str, Header(alias="X-Internal-Username", min_length=3, max_length=64)],
    token: Annotated[str, Header(alias="X-Internal-Token", min_length=1, max_length=256)],
    service: Annotated[InternalAuthService, Depends(get_internal_auth_service)],
) -> AuthenticatedPrincipal:
    try:
        return service.authenticate(username=username, token=token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_internal_credentials",
        ) from exc
