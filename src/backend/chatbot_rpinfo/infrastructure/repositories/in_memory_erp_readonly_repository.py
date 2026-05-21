from __future__ import annotations

from dataclasses import dataclass

from chatbot_rpinfo.domain.entities import ErpReadonlyQuery, ErpReadonlyResult, ErpRow


@dataclass(frozen=True, slots=True)
class AllowedErpReadonlyQuery:
    name: str
    source: str
    rows: tuple[ErpRow, ...]
    timeout_seconds: float
    max_rows: int
    wrapper_statement: str = "SET TRANSACTION READ ONLY"


class InMemoryErpReadonlyRepository:
    def __init__(self, allowlist: tuple[AllowedErpReadonlyQuery, ...]) -> None:
        self._allowlist = {entry.name: entry for entry in allowlist}

    @classmethod
    def default(cls, timeout_seconds: float, max_rows: int) -> InMemoryErpReadonlyRepository:
        return cls(
            allowlist=(
                AllowedErpReadonlyQuery(
                    name="inventory_risk_sample",
                    source="erp_readonly.fixture.inventory",
                    rows=(
                        {
                            "sku": "SKU-001",
                            "store_id": 2,
                            "stock": 12,
                            "days_without_sale": 7,
                        },
                    ),
                    timeout_seconds=timeout_seconds,
                    max_rows=max_rows,
                ),
                AllowedErpReadonlyQuery(
                    name="sales_summary_sample",
                    source="erp_readonly.fixture.sales",
                    rows=(
                        {
                            "store_id": 2,
                            "period": "30d",
                            "gross_sales": 1250.0,
                        },
                    ),
                    timeout_seconds=timeout_seconds,
                    max_rows=max_rows,
                ),
            )
        )

    def is_allowed(self, query_name: str) -> bool:
        return query_name in self._allowlist

    def execute(self, query: ErpReadonlyQuery) -> ErpReadonlyResult:
        allowed = self._allowlist[query.name]
        limit = min(query.limit, allowed.max_rows)
        return ErpReadonlyResult(
            query_name=query.name,
            source=allowed.source,
            rows=allowed.rows[:limit],
            read_only=allowed.wrapper_statement == "SET TRANSACTION READ ONLY",
            timeout_seconds=allowed.timeout_seconds,
            max_rows=allowed.max_rows,
        )
