from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from chatbot_rpinfo.application.services import SlidingWindowRateLimiter
from chatbot_rpinfo.domain.entities import InternalRole


class MutableClock:
    def __init__(self, value: float) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def _headers(username: str, token: str) -> dict[str, str]:
    return {
        "X-Internal-Username": username,
        "X-Internal-Token": token,
    }


def _install_limiter(
    client: TestClient,
    clock: MutableClock,
    *,
    default_limit: int = 1,
    comercial_limit: int = 2,
) -> None:
    app = client.app
    assert isinstance(app, FastAPI)
    app.state.rate_limiter = SlidingWindowRateLimiter(
        clock=clock,
        window_seconds=10,
        default_limit=default_limit,
        limits_by_role={
            InternalRole.COMERCIAL: comercial_limit,
            InternalRole.PREVENCAO: 2,
            InternalRole.ADMIN_TECNICO: 3,
            InternalRole.DIRECAO: 3,
        },
    )


def test_rate_limit_allows_requests_under_role_limit(client: TestClient) -> None:
    _install_limiter(client, MutableClock(100.0))

    first = client.get(
        "/api/v1/auth/internal/me",
        headers=_headers("rp-comercial", "test-comercial-token"),
    )
    second = client.get(
        "/api/v1/auth/internal/me",
        headers=_headers("rp-comercial", "test-comercial-token"),
    )

    assert first.status_code == 200
    assert second.status_code == 200


def test_rate_limit_returns_429_with_retry_after_and_audit_metadata(
    client: TestClient,
) -> None:
    _install_limiter(client, MutableClock(100.0))
    headers = _headers("rp-comercial", "test-comercial-token")

    assert client.get("/api/v1/auth/internal/me", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/internal/me", headers=headers).status_code == 200
    exceeded = client.get("/api/v1/auth/internal/me", headers=headers)

    assert exceeded.status_code == 429
    assert exceeded.headers["Retry-After"] == "10"
    assert exceeded.json() == {
        "detail": "rate_limit_exceeded",
        "limit": 2,
        "window_seconds": 10,
        "retry_after_seconds": 10,
        "role_used": "comercial",
    }

    app = client.app
    assert isinstance(app, FastAPI)
    audit_events = app.state.audit_event_repository.list_events()
    assert len(audit_events) == 1
    assert audit_events[0].rate_limit_hit is True
    assert audit_events[0].rate_limit_window_seconds == 10
    assert audit_events[0].role_used == "comercial"


def test_rate_limit_aggregates_authenticated_bucket_across_routes(
    client: TestClient,
) -> None:
    _install_limiter(client, MutableClock(100.0), comercial_limit=1)
    headers = _headers("rp-comercial", "test-comercial-token")

    first = client.get("/api/v1/auth/internal/me", headers=headers)
    exceeded = client.get("/api/v1/health", headers=headers)

    assert first.status_code == 200
    assert exceeded.status_code == 429
    assert exceeded.headers["Retry-After"] == "10"
    assert exceeded.json()["role_used"] == "comercial"


def test_rate_limit_resets_after_window(client: TestClient) -> None:
    clock = MutableClock(100.0)
    _install_limiter(client, clock)
    headers = _headers("rp-prevencao", "test-prevencao-token")

    assert client.get("/api/v1/auth/internal/me", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/internal/me", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/internal/me", headers=headers).status_code == 429

    clock.value = 111.0

    assert client.get("/api/v1/auth/internal/me", headers=headers).status_code == 200


def test_rate_limit_uses_default_bucket_for_requests_without_internal_headers(
    client: TestClient,
) -> None:
    _install_limiter(client, MutableClock(100.0), default_limit=1)

    assert client.get("/api/v1/health").status_code == 200
    exceeded = client.get("/api/v1/health")

    assert exceeded.status_code == 429
    assert exceeded.json()["role_used"] == "default"


def test_rate_limit_covers_admin_and_direcao_role_limits(client: TestClient) -> None:
    _install_limiter(client, MutableClock(100.0))

    for username, token in [
        ("rp-admin-tecnico", "test-admin-token"),
        ("rp-direcao", "test-direcao-token"),
    ]:
        headers = _headers(username, token)
        assert client.get("/api/v1/auth/internal/me", headers=headers).status_code == 200
        assert client.get("/api/v1/auth/internal/me", headers=headers).status_code == 200
        assert client.get("/api/v1/auth/internal/me", headers=headers).status_code == 200
        exceeded = client.get("/api/v1/auth/internal/me", headers=headers)
        assert exceeded.status_code == 429
        assert exceeded.json()["limit"] == 3
