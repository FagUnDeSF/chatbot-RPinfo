from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from chatbot_rpinfo.domain.entities.access import InternalRole


class AuditSource(StrEnum):
    ERP_READONLY = "erp_readonly"
    VENDAS = "vendas"
    ESTOQUE = "estoque"
    PREVENCAO = "prevencao"
    SISTEMA = "sistema"
    QA_ORCHESTRATOR = "qa_orchestrator"


class AuditResponseType(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_DATA = "insufficient_data"
    FORBIDDEN = "forbidden"
    ERROR = "error"


class FallbackReason(StrEnum):
    PROVIDER_INDISPONIVEL = "provider_indisponivel"
    BUDGET_EXCEEDED = "budget_exceeded"
    FORCED_BY_ADMIN = "forced_by_admin"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Audit event with NIVEL-3 expanded metadata (V5 §5.1 + Security #4).

    All LLM-related fields default to None/False to preserve backward
    compatibility with S001 events (stub-deterministico) that did not record
    these fields. CG-04 absolute: no raw payload (question literal, output
    completo do LLM) is ever stored - only structural metadata.
    """

    # Canonical S001 fields.
    event_id: str
    username: str
    role: InternalRole
    occurred_at: datetime
    intent: str
    source: AuditSource
    response_type: AuditResponseType
    insufficient_data: bool

    # NIVEL-3 V5 §5.1 (17 LLM-related fields) + Security ajuste #4 (3 fields:
    # request_id + correlation_id_upstream + refusal_evasion_attempted).
    provider_used: str | None = None
    model_used: str | None = None
    prompt_version: str | None = None
    cache_hit: bool = False
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    input_tokens_total: int = 0
    output_tokens_total: int = 0
    cost_usd: Decimal | None = None
    latency_ms_total: int = 0
    latency_ms_provider_call: int = 0
    escalation_requested: bool = False
    escalation_granted: bool = False
    pii_detectado_pre_egress: bool = False
    pii_redacted_pos_egress: bool = False
    pii_redacted_count: int = 0
    pii_redacted_categories: tuple[str, ...] = field(default_factory=tuple)
    content_policy_blocked: bool = False
    content_policy_pattern_id: str | None = None
    refusal_evasion_attempted: bool = False
    fallback_active: bool = False
    fallback_reason: FallbackReason | None = None
    request_id: str | None = None
    correlation_id_upstream: str | None = None
