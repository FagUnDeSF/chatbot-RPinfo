from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from chatbot_rpinfo.domain.entities.audit_event import FallbackReason
from chatbot_rpinfo.domain.entities.erp_readonly import ErpRow


class QaIntentKind(StrEnum):
    INVENTORY_RISK = "inventory_risk"
    SALES_SUMMARY = "sales_summary"
    UNKNOWN = "unknown"


class QaAnswerType(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_DATA = "insufficient_data"


class QaInsufficientReason(StrEnum):
    INTENT_NAO_RECONHECIDO = "intent_nao_reconhecido"
    DADO_INDISPONIVEL = "dado_indisponivel"
    PROVIDER_INDISPONIVEL = "provider_indisponivel"
    BUDGET_EXCEEDED = "budget_exceeded"
    FORCED_BY_ADMIN = "forced_by_admin"


@dataclass(frozen=True, slots=True)
class QaIntent:
    kind: QaIntentKind
    erp_query_name: str | None


@dataclass(frozen=True, slots=True)
class QaAnswer:
    answer_id: str
    answer_type: QaAnswerType
    intent: QaIntent
    rows: tuple[ErpRow, ...]
    source: str | None
    premises: tuple[str, ...]
    reason: QaInsufficientReason | None
    prompt_version: str
    provider: str
    model: str | None
    # V5 NIVEL-3 surfaced fields - propagated to response payload + header
    # `X-LLM-Fallback` / `X-LLM-Escalation` so callers can inspect router
    # decisions without scraping audit storage (4 elements of anti-fallback-
    # silencioso satisfied: declaracao + log + response payload + alerta).
    fallback_active: bool = False
    fallback_reason: FallbackReason | None = None
    escalation_requested: bool = False
    escalation_granted: bool = False
    pii_redacted_pos_egress: bool = False
    pii_redacted_categories: tuple[str, ...] = field(default_factory=tuple)
