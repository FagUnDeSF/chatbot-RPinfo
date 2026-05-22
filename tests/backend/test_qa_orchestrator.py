from __future__ import annotations

from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_qa_ask_positivo_inventory_risk_retorna_resposta_com_fonte_e_premissas(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/qa/ask",
        headers={
            "X-Internal-Username": "rp-prevencao",
            "X-Internal-Token": "test-prevencao-token",
            "Idempotency-Key": "qa-golden-positive-001",
        },
        json={"question": "Qual o risco de estoque parado da loja 2?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer_type"] == "answered"
    assert body["intent"]["kind"] == "inventory_risk"
    assert body["intent"]["erp_query_name"] == "inventory_risk_sample"
    assert body["reason"] is None
    assert body["source"] == "erp_readonly.fixture.inventory"
    assert len(body["rows"]) == 1
    assert body["rows"][0]["sku"] == "SKU-001"
    assert len(body["premises"]) >= 1
    assert any("SKU-001" in premise for premise in body["premises"])
    assert any("loja" in premise.lower() for premise in body["premises"])
    assert body["prompt_version"] == "0.2.0"
    assert body["provider"] == "stub-deterministico"
    assert body["model"] is None


def test_qa_ask_negativa_intent_desconhecido_retorna_motivo(client: TestClient) -> None:
    response = client.post(
        "/api/v1/qa/ask",
        headers={
            "X-Internal-Username": "rp-comercial",
            "X-Internal-Token": "test-comercial-token",
            "Idempotency-Key": "qa-golden-negative-002",
        },
        json={"question": "Qual a previsao do tempo amanha?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer_type"] == "insufficient_data"
    assert body["intent"]["kind"] == "unknown"
    assert body["intent"]["erp_query_name"] is None
    assert body["reason"] == "intent_nao_reconhecido"
    assert body["source"] is None
    assert body["rows"] == []
    assert body["premises"] == []
    assert body["prompt_version"] == "0.2.0"
    assert body["provider"] == "stub-deterministico"


def test_qa_ask_negativa_dado_indisponivel_quando_query_retorna_zero_linhas(
    client: TestClient,
) -> None:
    # Sales intent classifier maps to sales_summary_sample, which has 1 row in
    # the default fixture. Para cobrir o ramo `dado_indisponivel` reproduzivel,
    # injetamos uma fixture vazia para inventory_risk_sample via app.state.
    from chatbot_rpinfo.infrastructure.repositories import InMemoryErpReadonlyRepository
    from chatbot_rpinfo.infrastructure.repositories.in_memory_erp_readonly_repository import (
        AllowedErpReadonlyQuery,
    )

    empty_repo = InMemoryErpReadonlyRepository(
        allowlist=(
            AllowedErpReadonlyQuery(
                name="inventory_risk_sample",
                source="erp_readonly.fixture.inventory.empty",
                rows=(),
                timeout_seconds=5.0,
                max_rows=100,
            ),
        )
    )
    cast(FastAPI, client.app).state.erp_readonly_repository = empty_repo

    response = client.post(
        "/api/v1/qa/ask",
        headers={
            "X-Internal-Username": "rp-prevencao",
            "X-Internal-Token": "test-prevencao-token",
            "Idempotency-Key": "qa-golden-empty-003",
        },
        json={"question": "Tem produto parado em estoque?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer_type"] == "insufficient_data"
    assert body["intent"]["kind"] == "inventory_risk"
    assert body["reason"] == "dado_indisponivel"
    assert body["source"] == "erp_readonly.fixture.inventory.empty"
    assert body["rows"] == []
    assert body["premises"] == []


def test_qa_ask_registra_audit_metadado_por_chamada(client: TestClient) -> None:
    client.post(
        "/api/v1/qa/ask",
        headers={
            "X-Internal-Username": "rp-prevencao",
            "X-Internal-Token": "test-prevencao-token",
            "Idempotency-Key": "qa-audit-trace-001",
        },
        json={"question": "Qual o risco de estoque parado?"},
    )

    repo = cast(FastAPI, client.app).state.audit_event_repository
    events = repo.list_events()
    qa_events = [event for event in events if event.source.value == "qa_orchestrator"]
    assert len(qa_events) == 1
    assert qa_events[0].intent == "qa_orchestrator:inventory_risk"
    assert qa_events[0].response_type.value == "answered"
    assert qa_events[0].insufficient_data is False
