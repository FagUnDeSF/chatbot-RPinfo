from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from chatbot_rpinfo.domain.entities.access import InternalRole


class AuditSource(StrEnum):
    ERP_READONLY = "erp_readonly"
    VENDAS = "vendas"
    ESTOQUE = "estoque"
    PREVENCAO = "prevencao"
    SISTEMA = "sistema"


class AuditResponseType(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_DATA = "insufficient_data"
    FORBIDDEN = "forbidden"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    username: str
    role: InternalRole
    occurred_at: datetime
    intent: str
    source: AuditSource
    response_type: AuditResponseType
    insufficient_data: bool
