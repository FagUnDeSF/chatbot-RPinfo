from __future__ import annotations

from typing import Protocol

from chatbot_rpinfo.domain.entities import ErpReadonlyQuery, ErpReadonlyResult


class ErpReadonlyRepository(Protocol):
    def is_allowed(self, query_name: str) -> bool:
        raise NotImplementedError

    def execute(self, query: ErpReadonlyQuery) -> ErpReadonlyResult:
        raise NotImplementedError
