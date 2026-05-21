from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chatbot_rpinfo.config import load_settings
from chatbot_rpinfo.presentation.api import create_app


@pytest.fixture()
def client() -> TestClient:
    token_source = {
        "INTERNAL_AUTH_DIRECAO_TOKEN": "test-direcao-token",
        "INTERNAL_AUTH_COMERCIAL_TOKEN": "test-comercial-token",
        "INTERNAL_AUTH_PREVENCAO_TOKEN": "test-prevencao-token",
        "INTERNAL_AUTH_ADMIN_TECNICO_TOKEN": "test-admin-token",
    }
    app = create_app(
        load_settings(
            {
                "APP_NAME": "chatbot-RPinfo",
                "APP_ENV": "test",
                "APP_VERSION": "0.1.0",
            }
        ),
        token_source=token_source,
    )
    return TestClient(app)


@pytest.mark.parametrize(
    ("username", "token", "role"),
    [
        ("rp-direcao", "test-direcao-token", "direcao"),
        ("rp-comercial", "test-comercial-token", "comercial"),
        ("rp-prevencao", "test-prevencao-token", "prevencao"),
        ("rp-admin-tecnico", "test-admin-token", "admin-tecnico"),
    ],
)
def test_internal_users_authenticate_with_minimum_profiles(
    client: TestClient,
    username: str,
    token: str,
    role: str,
) -> None:
    response = client.post(
        "/api/v1/auth/internal/login",
        json={"username": username, "access_token": token},
    )

    assert response.status_code == 200
    assert response.json()["username"] == username
    assert response.json()["role"] == role
    assert "access_token" not in response.json()


def test_internal_auth_rejects_invalid_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/internal/login",
        json={"username": "rp-direcao", "access_token": "wrong-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_internal_credentials"}


def test_current_user_requires_internal_headers(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/internal/me",
        headers={
            "X-Internal-Username": "rp-admin-tecnico",
            "X-Internal-Token": "test-admin-token",
        },
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin-tecnico"


def test_query_audit_records_metadata_without_sensitive_payload(client: TestClient) -> None:
    response = client.post(
        "/api/v1/audit/query-events",
        headers={
            "X-Internal-Username": "rp-comercial",
            "X-Internal-Token": "test-comercial-token",
            "Idempotency-Key": "audit-test-001",
        },
        json={
            "intent": "consulta de estoque agregada",
            "source": "estoque",
            "response_type": "answered",
            "insufficient_data": False,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "rp-comercial"
    assert body["role"] == "comercial"
    assert body["source"] == "estoque"
    assert body["intent"] == "consulta de estoque agregada"
    assert "payload" not in body
    assert "test-comercial-token" not in response.text


def test_query_audit_is_idempotent_per_idempotency_key(client: TestClient) -> None:
    payload = {
        "intent": "consulta sem dado suficiente",
        "source": "erp_readonly",
        "response_type": "insufficient_data",
        "insufficient_data": True,
    }
    headers = {
        "X-Internal-Username": "rp-direcao",
        "X-Internal-Token": "test-direcao-token",
        "Idempotency-Key": "audit-test-002",
    }

    first_response = client.post("/api/v1/audit/query-events", headers=headers, json=payload)
    second_response = client.post("/api/v1/audit/query-events", headers=headers, json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert second_response.json()["event_id"] == first_response.json()["event_id"]


def test_query_audit_rejects_raw_payload_field(client: TestClient) -> None:
    response = client.post(
        "/api/v1/audit/query-events",
        headers={
            "X-Internal-Username": "rp-direcao",
            "X-Internal-Token": "test-direcao-token",
            "Idempotency-Key": "audit-test-003",
        },
        json={
            "intent": "consulta com payload indevido",
            "source": "erp_readonly",
            "response_type": "answered",
            "insufficient_data": False,
            "payload": {"cpf": "00000000000"},
        },
    )

    assert response.status_code == 422


def test_rbac_blocks_profile_from_unapproved_source(client: TestClient) -> None:
    response = client.post(
        "/api/v1/audit/query-events",
        headers={
            "X-Internal-Username": "rp-comercial",
            "X-Internal-Token": "test-comercial-token",
            "Idempotency-Key": "audit-test-004",
        },
        json={
            "intent": "consulta de prevencao",
            "source": "prevencao",
            "response_type": "answered",
            "insufficient_data": False,
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "role_cannot_record_source"}
