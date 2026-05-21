from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from chatbot_rpinfo.domain.entities import (
    ErpParameterValue,
    ErpReadonlyQuery,
    ErpReadonlyResult,
    ErpRow,
)


class ErpReadonlyQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query_name: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_]+$")
    parameters: dict[str, ErpParameterValue] = Field(default_factory=dict)
    limit: int = Field(default=100, ge=1, le=1000)

    def to_domain(self) -> ErpReadonlyQuery:
        return ErpReadonlyQuery(name=self.query_name, parameters=self.parameters, limit=self.limit)


class ErpReadonlyQueryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_name: str
    source: str
    read_only: bool
    timeout_seconds: float
    max_rows: int
    row_count: int
    rows: tuple[ErpRow, ...]

    @classmethod
    def from_domain(cls, result: ErpReadonlyResult) -> ErpReadonlyQueryResponse:
        return cls(
            query_name=result.query_name,
            source=result.source,
            read_only=result.read_only,
            timeout_seconds=result.timeout_seconds,
            max_rows=result.max_rows,
            row_count=result.row_count,
            rows=result.rows,
        )
