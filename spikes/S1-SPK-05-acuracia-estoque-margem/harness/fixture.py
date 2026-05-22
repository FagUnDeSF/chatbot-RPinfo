"""Fixture sintetica do spike S1-SPK-05.

A fixture estende a allowlist em-memoria da camada `erp_readonly` para
incluir duas queries especificas do spike, sem tocar a allowlist runtime
do backend nem expandir a fronteira real. Mantida a interface canonica
`AllowedErpReadonlyQuery` para que o consumo passe pela mesma rota de
validacao/execucao do `ErpReadonlyService`.

Premissas declaradas:
- Dados sao sinteticos (sem PII, sem mapping para SKU real, sem nome de
  loja, sem CPF/CNPJ). Codigos SKU usam prefixo `SKU-S1SPK05-` para
  marcar origem do spike.
- Janela temporal: snapshot unico tomado em `as_of_date` declarado por
  metrica; nao ha replay historico.
- Filtros aplicados: nenhum (a amostra inteira da query e passada para a
  regra; filtros sao aplicados pela regra, nao pela fonte).
"""
from __future__ import annotations

from chatbot_rpinfo.domain.entities import ErpRow
from chatbot_rpinfo.infrastructure.repositories.in_memory_erp_readonly_repository import (
    AllowedErpReadonlyQuery,
    InMemoryErpReadonlyRepository,
)

SPIKE_AS_OF_DATE = "2026-05-21"

INVENTORY_RISK_SPIKE_QUERY_NAME = "inventory_risk_spike_S1_C05"
SALES_SUMMARY_SPIKE_QUERY_NAME = "sales_summary_spike_S1_C05"

_INVENTORY_RISK_ROWS: tuple[ErpRow, ...] = (
    {"sku": "SKU-S1SPK05-001", "store_id": 1, "stock": 12, "days_without_sale": 4},
    {"sku": "SKU-S1SPK05-002", "store_id": 1, "stock": 5, "days_without_sale": 95},
    {"sku": "SKU-S1SPK05-003", "store_id": 1, "stock": 0, "days_without_sale": 180},
    {"sku": "SKU-S1SPK05-004", "store_id": 2, "stock": 22, "days_without_sale": 91},
    {"sku": "SKU-S1SPK05-005", "store_id": 2, "stock": 7, "days_without_sale": 14},
    {"sku": "SKU-S1SPK05-006", "store_id": 2, "stock": 3, "days_without_sale": 365},
    {"sku": "SKU-S1SPK05-007", "store_id": 3, "stock": 18, "days_without_sale": 0},
    {"sku": "SKU-S1SPK05-008", "store_id": 3, "stock": 11, "days_without_sale": 122},
    {"sku": "SKU-S1SPK05-009", "store_id": 3, "stock": 1, "days_without_sale": 89},
    {"sku": "SKU-S1SPK05-010", "store_id": 3, "stock": 9, "days_without_sale": 210},
)

_SALES_SUMMARY_ROWS: tuple[ErpRow, ...] = (
    {"store_id": 1, "period": "30d", "gross_sales": 980.0},
    {"store_id": 2, "period": "30d", "gross_sales": 1450.5},
    {"store_id": 3, "period": "30d", "gross_sales": 1230.0},
)


def build_spike_repository(timeout_seconds: float, max_rows: int) -> InMemoryErpReadonlyRepository:
    """Constroi repositorio em-memoria com allowlist estendida do spike.

    Nao toca a allowlist runtime do backend. Mantem a mesma interface
    `AllowedErpReadonlyQuery` para que `ErpReadonlyService.execute` aplique
    a validacao canonica (allowlist + limit) sobre a amostra do spike.
    """
    allowlist = (
        AllowedErpReadonlyQuery(
            name=INVENTORY_RISK_SPIKE_QUERY_NAME,
            source="erp_readonly.fixture.spike_S1_C05.inventory",
            rows=_INVENTORY_RISK_ROWS,
            timeout_seconds=timeout_seconds,
            max_rows=max_rows,
        ),
        AllowedErpReadonlyQuery(
            name=SALES_SUMMARY_SPIKE_QUERY_NAME,
            source="erp_readonly.fixture.spike_S1_C05.sales",
            rows=_SALES_SUMMARY_ROWS,
            timeout_seconds=timeout_seconds,
            max_rows=max_rows,
        ),
    )
    return InMemoryErpReadonlyRepository(allowlist=allowlist)
