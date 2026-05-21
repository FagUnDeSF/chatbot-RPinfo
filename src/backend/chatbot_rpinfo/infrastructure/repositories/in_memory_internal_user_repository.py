from __future__ import annotations

from collections.abc import Iterable

from chatbot_rpinfo.domain.entities import InternalUser


class InMemoryInternalUserRepository:
    def __init__(self, users: Iterable[InternalUser]) -> None:
        self._users_by_username = {user.username: user for user in users}

    def get_by_username(self, username: str) -> InternalUser | None:
        return self._users_by_username.get(username)
