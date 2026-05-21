from __future__ import annotations

from fastapi.testclient import TestClient


def test_erp_query_passes_through_readonly_module(client: TestClient) -> None:
    response = client.post(
        "/api/v1/erp-readonly/query",
        headers={
            "X-Internal-Username": "rp-prevencao",
            "X-Internal-Token": "test-prevencao-token",
            "Idempotency-Key": "erp-query-001",
        },
        json={"query_name": "inventory_risk_sample", "parameters": {}, "limit": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query_name"] == "inventory_risk_sample"
    assert body["read_only"] is True
    assert body["timeout_seconds"] == 5.0
    assert body["max_rows"] == 100
    assert body["source"] == "erp_readonly.fixture.inventory"
    assert body["row_count"] == 1


def test_erp_query_records_audit_metadata_without_payload(client: TestClient) -> None:
    response = client.post(
        "/api/v1/erp-readonly/query",
        headers={
            "X-Internal-Username": "rp-direcao",
            "X-Internal-Token": "test-direcao-token",
            "Idempotency-Key": "erp-query-002",
        },
        json={
            "query_name": "sales_summary_sample",
            "parameters": {"cpf": "00000000000"},
            "limit": 10,
        },
    )

    assert response.status_code == 200

    audit_response = client.post(
        "/api/v1/audit/query-events",
        headers={
            "X-Internal-Username": "rp-direcao",
            "X-Internal-Token": "test-direcao-token",
            "Idempotency-Key": "erp-query-002",
        },
        json={
            "intent": "erp_readonly:sales_summary_sample",
            "source": "erp_readonly",
            "response_type": "answered",
            "insufficient_data": False,
            "payload": {"cpf": "00000000000"},
        },
    )

    assert audit_response.status_code == 422


def test_erp_query_rejects_non_allowlisted_query(client: TestClient) -> None:
    response = client.post(
        "/api/v1/erp-readonly/query",
        headers={
            "X-Internal-Username": "rp-admin-tecnico",
            "X-Internal-Token": "test-admin-token",
            "Idempotency-Key": "erp-query-003",
        },
        json={"query_name": "drop_table_attempt", "parameters": {}, "limit": 10},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "query_not_allowlisted"}


def test_erp_query_enforces_max_rows(client: TestClient) -> None:
    response = client.post(
        "/api/v1/erp-readonly/query",
        headers={
            "X-Internal-Username": "rp-admin-tecnico",
            "X-Internal-Token": "test-admin-token",
            "Idempotency-Key": "erp-query-004",
        },
        json={"query_name": "inventory_risk_sample", "parameters": {}, "limit": 101},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "limit_exceeds_configured_max_rows"}
