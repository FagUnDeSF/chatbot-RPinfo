from __future__ import annotations

import os
from collections.abc import Mapping

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from chatbot_rpinfo.config import AppSettings, load_settings
from chatbot_rpinfo.domain.entities import InternalUser
from chatbot_rpinfo.infrastructure.repositories import (
    InMemoryAuditEventRepository,
    InMemoryErpReadonlyRepository,
    InMemoryInternalUserRepository,
)
from chatbot_rpinfo.presentation.controllers.audit_controller import router as audit_router
from chatbot_rpinfo.presentation.controllers.auth_controller import router as auth_router
from chatbot_rpinfo.presentation.controllers.erp_readonly_controller import (
    router as erp_readonly_router,
)
from chatbot_rpinfo.presentation.controllers.health_controller import router as health_router
from chatbot_rpinfo.presentation.dependencies import get_settings

_SENSITIVE_ERROR_TAG = "sensitive_identifier_detected"


def _redact_validation_errors(
    errors: list[dict[str, object]],
) -> list[dict[str, object]]:
    redacted: list[dict[str, object]] = []
    for error in errors:
        message = str(error.get("msg", ""))
        if _SENSITIVE_ERROR_TAG in message:
            sanitized = {k: v for k, v in error.items() if k not in {"input", "ctx"}}
            sanitized["input"] = "<redacted:sensitive_identifier>"
            redacted.append(sanitized)
        else:
            redacted.append(error)
    return redacted


def create_app(
    settings: AppSettings | None = None,
    token_source: Mapping[str, str] | None = None,
) -> FastAPI:
    resolved_settings = settings or load_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{resolved_settings.api_prefix}/openapi.json",
    )
    internal_users = tuple(
        InternalUser(
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            token_env_var=user.token_env_var,
        )
        for user in resolved_settings.internal_users
    )
    app.state.internal_user_repository = InMemoryInternalUserRepository(internal_users)
    app.state.audit_event_repository = InMemoryAuditEventRepository()
    app.state.erp_readonly_repository = InMemoryErpReadonlyRepository.default(
        timeout_seconds=resolved_settings.erp_readonly_timeout_seconds,
        max_rows=resolved_settings.erp_readonly_max_rows,
    )
    app.state.token_source = os.environ if token_source is None else token_source
    app.dependency_overrides[get_settings] = lambda: resolved_settings

    @app.exception_handler(RequestValidationError)
    async def _redact_sensitive_validation_errors(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        raw_errors: list[dict[str, object]] = [dict(error) for error in exc.errors()]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": _redact_validation_errors(raw_errors)},
        )

    app.include_router(auth_router, prefix=resolved_settings.api_prefix)
    app.include_router(audit_router, prefix=resolved_settings.api_prefix)
    app.include_router(erp_readonly_router, prefix=resolved_settings.api_prefix)
    app.include_router(health_router, prefix=resolved_settings.api_prefix)
    return app
