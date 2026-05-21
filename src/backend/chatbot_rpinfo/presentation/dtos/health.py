from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from chatbot_rpinfo.domain.entities import HealthStatus


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    service: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    version: str = Field(min_length=1)

    @classmethod
    def from_domain(cls, status: HealthStatus) -> HealthResponse:
        return cls(
            status=status.status,
            service=status.service,
            environment=status.environment,
            version=status.version,
        )

