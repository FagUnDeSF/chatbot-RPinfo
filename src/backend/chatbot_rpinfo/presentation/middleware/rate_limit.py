from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast
from uuid import uuid4

from fastapi import Request, status
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from chatbot_rpinfo.application.services import (
    AuditService,
    AuthenticationError,
    InternalAuthService,
    SlidingWindowRateLimiter,
)
from chatbot_rpinfo.domain.entities import AuthenticatedPrincipal
from chatbot_rpinfo.domain.repositories import AuditEventRepository


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, api_prefix: str) -> None:
        super().__init__(app)
        self._api_prefix = api_prefix.rstrip("/")
        self._excluded_paths = {
            f"{self._api_prefix}/openapi.json",
        }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self._should_rate_limit(request.url.path):
            return await call_next(request)

        principal = self._authenticate_if_present(request)
        decision = self._limiter(request).check(
            bucket_key=self._bucket_key(request, principal),
            role=principal.user.role if principal is not None else None,
            route_key=request.url.path,
        )
        if decision.allowed:
            return await call_next(request)

        if principal is not None:
            self._audit_service(request).record_rate_limit_hit(
                principal=principal,
                idempotency_key=f"rate-limit-hit-{uuid4()}",
                window_seconds=decision.window_seconds,
            )

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(decision.retry_after_seconds)},
            content={
                "detail": "rate_limit_exceeded",
                "limit": decision.limit,
                "window_seconds": decision.window_seconds,
                "retry_after_seconds": decision.retry_after_seconds,
                "role_used": decision.role_used,
            },
        )

    def _should_rate_limit(self, path: str) -> bool:
        return path.startswith(f"{self._api_prefix}/") and path not in self._excluded_paths

    @staticmethod
    def _authenticate_if_present(request: Request) -> AuthenticatedPrincipal | None:
        username = request.headers.get("X-Internal-Username")
        token = request.headers.get("X-Internal-Token")
        if username is None or token is None:
            return None

        service = InternalAuthService(
            user_repository=request.app.state.internal_user_repository,
            token_source=request.app.state.token_source,
        )
        try:
            return service.authenticate(username=username, token=token)
        except AuthenticationError:
            return None

    @staticmethod
    def _bucket_key(request: Request, principal: AuthenticatedPrincipal | None) -> str:
        if principal is not None:
            return principal.user.username
        username = request.headers.get("X-Internal-Username")
        return username or "anonymous"

    @staticmethod
    def _limiter(request: Request) -> SlidingWindowRateLimiter:
        return cast(SlidingWindowRateLimiter, request.app.state.rate_limiter)

    @staticmethod
    def _audit_service(request: Request) -> AuditService:
        repository = cast(AuditEventRepository, request.app.state.audit_event_repository)
        return AuditService(audit_event_repository=repository)
