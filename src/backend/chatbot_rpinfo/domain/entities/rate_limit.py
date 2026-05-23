from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    window_seconds: int
    retry_after_seconds: int
    role_used: str
    current_count: int
