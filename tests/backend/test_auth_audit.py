from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


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


@pytest.mark.parametrize(
    ("idempotency_key", "intent"),
    [
        ("audit-sensitive-cpf-raw", "consulta CPF 00000000000"),
        ("audit-sensitive-cpf-fmt", "consulta CPF 000.000.000-00"),
        ("audit-sensitive-cnpj-raw", "consulta CNPJ 00000000000000"),
        ("audit-sensitive-cnpj-fmt", "consulta CNPJ 00.000.000/0000-00"),
        ("audit-sensitive-phone", "contato WhatsApp (11) 99999-9999"),
        ("audit-sensitive-phone-e164", "contato 5511999999999"),
        ("audit-sensitive-rg-sp-fmt-x-upper", "consulta RG 12.345.678-X"),
        ("audit-sensitive-rg-sp-fmt-x-lower", "consulta RG 12.345.678-x"),
        ("audit-sensitive-rg-sp-fmt-digit", "consulta RG 12.345.678-9"),
        ("audit-sensitive-rg-sp-fmt-zero", "cliente 00.000.000-0 nao localizado"),
    ],
)
def test_query_audit_rejects_sensitive_identifiers_in_intent(
    client: TestClient,
    idempotency_key: str,
    intent: str,
) -> None:
    response = client.post(
        "/api/v1/audit/query-events",
        headers={
            "X-Internal-Username": "rp-direcao",
            "X-Internal-Token": "test-direcao-token",
            "Idempotency-Key": idempotency_key,
        },
        json={
            "intent": intent,
            "source": "erp_readonly",
            "response_type": "answered",
            "insufficient_data": False,
        },
    )

    assert response.status_code == 422
    assert "sensitive_identifier_detected" in response.text
    assert intent not in response.text


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
