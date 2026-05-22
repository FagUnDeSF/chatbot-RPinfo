from __future__ import annotations

from typing import Protocol

from chatbot_rpinfo.domain.entities import QaIntent, QaIntentKind

_KEYWORDS_TO_INTENT: tuple[tuple[QaIntentKind, str, tuple[str, ...]], ...] = (
    (
        QaIntentKind.INVENTORY_RISK,
        "inventory_risk_sample",
        ("estoque", "risco", "parado", "sem venda", "inventario"),
    ),
    (
        QaIntentKind.SALES_SUMMARY,
        "sales_summary_sample",
        ("venda", "vendas", "faturamento", "receita", "vendido"),
    ),
)


class IntentClassifier(Protocol):
    def classify(self, question: str) -> QaIntent:
        ...


class DeterministicKeywordIntentClassifier:
    def classify(self, question: str) -> QaIntent:
        normalized = question.casefold()
        for kind, erp_query_name, keywords in _KEYWORDS_TO_INTENT:
            if any(keyword in normalized for keyword in keywords):
                return QaIntent(kind=kind, erp_query_name=erp_query_name)
        return QaIntent(kind=QaIntentKind.UNKNOWN, erp_query_name=None)
