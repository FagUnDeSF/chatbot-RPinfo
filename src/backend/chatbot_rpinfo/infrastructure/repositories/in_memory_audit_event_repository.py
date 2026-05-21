from __future__ import annotations

from chatbot_rpinfo.domain.entities import AuditEvent


class InMemoryAuditEventRepository:
    def __init__(self) -> None:
        self._events_by_idempotency_key: dict[str, AuditEvent] = {}

    def save_once(self, idempotency_key: str, event: AuditEvent) -> AuditEvent:
        existing_event = self._events_by_idempotency_key.get(idempotency_key)
        if existing_event is not None:
            return existing_event
        self._events_by_idempotency_key[idempotency_key] = event
        return event

    def list_events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events_by_idempotency_key.values())
