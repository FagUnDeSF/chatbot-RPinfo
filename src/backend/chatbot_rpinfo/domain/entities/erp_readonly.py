from __future__ import annotations

from dataclasses import dataclass

ErpParameterValue = str | int | float | bool | None
ErpRow = dict[str, ErpParameterValue]


@dataclass(frozen=True, slots=True)
class ErpReadonlyQuery:
    name: str
    parameters: dict[str, ErpParameterValue]
    limit: int


@dataclass(frozen=True, slots=True)
class ErpReadonlyResult:
    query_name: str
    source: str
    rows: tuple[ErpRow, ...]
    read_only: bool
    timeout_seconds: float
    max_rows: int

    @property
    def row_count(self) -> int:
        return len(self.rows)
