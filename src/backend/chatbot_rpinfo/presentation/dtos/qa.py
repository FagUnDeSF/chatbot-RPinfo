from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from chatbot_rpinfo.domain.entities import (
    ErpRow,
    FallbackReason,
    QaAnswer,
    QaAnswerType,
    QaInsufficientReason,
    QaIntentKind,
)


class QaAskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    question: str = Field(min_length=3, max_length=500)


class QaIntentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: QaIntentKind
    erp_query_name: str | None


class QaAskResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer_id: str
    answer_type: QaAnswerType
    intent: QaIntentResponse
    rows: tuple[ErpRow, ...]
    source: str | None
    premises: tuple[str, ...]
    reason: QaInsufficientReason | None
    prompt_version: str
    provider: str
    model: str | None
    fallback_active: bool = False
    fallback_reason: FallbackReason | None = None
    escalation_requested: bool = False
    escalation_granted: bool = False
    pii_redacted_pos_egress: bool = False
    pii_redacted_categories: tuple[str, ...] = ()

    @classmethod
    def from_domain(cls, answer: QaAnswer) -> QaAskResponse:
        return cls(
            answer_id=answer.answer_id,
            answer_type=answer.answer_type,
            intent=QaIntentResponse(
                kind=answer.intent.kind,
                erp_query_name=answer.intent.erp_query_name,
            ),
            rows=answer.rows,
            source=answer.source,
            premises=answer.premises,
            reason=answer.reason,
            prompt_version=answer.prompt_version,
            provider=answer.provider,
            model=answer.model,
            fallback_active=answer.fallback_active,
            fallback_reason=answer.fallback_reason,
            escalation_requested=answer.escalation_requested,
            escalation_granted=answer.escalation_granted,
            pii_redacted_pos_egress=answer.pii_redacted_pos_egress,
            pii_redacted_categories=answer.pii_redacted_categories,
        )
