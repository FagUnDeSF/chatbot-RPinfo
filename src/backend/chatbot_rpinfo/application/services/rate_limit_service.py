from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping
from math import ceil
from threading import Lock
from time import monotonic

from chatbot_rpinfo.domain.entities import InternalRole, RateLimitDecision

RateLimitBucket = tuple[str, str, str]


class SlidingWindowRateLimiter:
    def __init__(
        self,
        *,
        clock: Callable[[], float] | None = None,
        window_seconds: int = 3600,
        default_limit: int = 100,
        limits_by_role: Mapping[InternalRole, int] | None = None,
    ) -> None:
        self._clock = monotonic if clock is None else clock
        self._window_seconds = window_seconds
        self._default_limit = default_limit
        self._limits_by_role = dict(limits_by_role or _default_role_limits())
        self._hits_by_bucket: dict[RateLimitBucket, deque[float]] = {}
        self._lock = Lock()

    @property
    def window_seconds(self) -> int:
        return self._window_seconds

    def check(
        self,
        *,
        bucket_key: str,
        role: InternalRole | None,
        route_key: str,
    ) -> RateLimitDecision:
        now = self._clock()
        role_used = role.value if role is not None else "default"
        limit = (
            self._default_limit
            if role is None
            else self._limits_by_role.get(role, self._default_limit)
        )
        bucket = (bucket_key, role_used, route_key)

        with self._lock:
            hits = self._hits_by_bucket.setdefault(bucket, deque())
            cutoff = now - self._window_seconds
            while hits and hits[0] <= cutoff:
                hits.popleft()

            if len(hits) >= limit:
                retry_after = max(1, ceil(hits[0] + self._window_seconds - now))
                return RateLimitDecision(
                    allowed=False,
                    limit=limit,
                    window_seconds=self._window_seconds,
                    retry_after_seconds=retry_after,
                    role_used=role_used,
                    current_count=len(hits),
                )

            hits.append(now)
            return RateLimitDecision(
                allowed=True,
                limit=limit,
                window_seconds=self._window_seconds,
                retry_after_seconds=0,
                role_used=role_used,
                current_count=len(hits),
            )


def _default_role_limits() -> dict[InternalRole, int]:
    return {
        InternalRole.COMERCIAL: 60,
        InternalRole.PREVENCAO: 60,
        InternalRole.ADMIN_TECNICO: 200,
        InternalRole.DIRECAO: 200,
    }
