from __future__ import annotations

from typing import Protocol

from chatbot_rpinfo.domain.entities import AuditEvent


class AuditEventRepository(Protocol):
    def save_once(self, idempotency_key: str, event: AuditEvent) -> AuditEvent:
        raise NotImplementedError

    def list_events(self) -> tuple[AuditEvent, ...]:
        raise NotImplementedError
