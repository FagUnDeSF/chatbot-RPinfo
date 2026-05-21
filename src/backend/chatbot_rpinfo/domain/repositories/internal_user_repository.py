from __future__ import annotations

from typing import Protocol

from chatbot_rpinfo.domain.entities import InternalUser


class InternalUserRepository(Protocol):
    def get_by_username(self, username: str) -> InternalUser | None:
        raise NotImplementedError
