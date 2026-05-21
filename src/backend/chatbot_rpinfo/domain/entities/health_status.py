from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class HealthStatus:
    status: Literal["ok"]
    service: str
    environment: str
    version: str

