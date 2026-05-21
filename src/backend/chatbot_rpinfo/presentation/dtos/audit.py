from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chatbot_rpinfo.domain.entities import AuditEvent, AuditResponseType, AuditSource, InternalRole
from chatbot_rpinfo.domain.policies import assert_no_sensitive_identifiers


class AuditQueryEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    intent: str = Field(min_length=3, max_length=120)
    source: AuditSource
    response_type: AuditResponseType
    insufficient_data: bool

    @field_validator("intent")
    @classmethod
    def _intent_must_not_carry_sensitive_identifiers(cls, value: str) -> str:
        return assert_no_sensitive_identifiers(value)


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    username: str
    role: InternalRole
    occurred_at: datetime
    intent: str
    source: AuditSource
    response_type: AuditResponseType
    insufficient_data: bool

    @classmethod
    def from_domain(cls, event: AuditEvent) -> AuditEventResponse:
        return cls(
            event_id=event.event_id,
            username=event.username,
            role=event.role,
            occurred_at=event.occurred_at,
            intent=event.intent,
            source=event.source,
            response_type=event.response_type,
            insufficient_data=event.insufficient_data,
        )
