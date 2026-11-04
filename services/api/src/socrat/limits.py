"""A small sliding-window limiter for endpoints that are cheap per call but open to abuse.

Model calls are already limited by ``assistant.budget`` (stored in the database, so every
process shares it). This is for the rest: simulations, diagnostics and similar. The window
lives in the memory of one process, so with N API processes a learner can make up to N times
the limit; that is deliberate for now (no Redis is provisioned) and is stated in the plan.
Swap ``LIMITER`` for a shared implementation with the same ``allow`` signature when one exists.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException


class Limiter:
    def __init__(self, max_keys: int = 50_000) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._max_keys = max_keys

    def allow(self, key: str, limit: int, window: float, at: float | None = None) -> bool:
        at = time.time() if at is None else at
        hits = self._hits[key]
        while hits and hits[0] <= at - window:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(at)
        if len(self._hits) > self._max_keys:  # forget idle keys so memory stays bounded
            for stale in [k for k, v in self._hits.items() if not v or v[-1] <= at - window]:
                del self._hits[stale]
        return True

    def clear(self) -> None:
        self._hits.clear()


LIMITER = Limiter()


def enforce(scope: str, user_id: str, limit: int, window: float) -> None:
    """Raise 429 ``rate_limited`` when this learner has used up ``limit`` calls in ``window`` s.
    A limit of 0 turns the check off."""
    if limit and not LIMITER.allow(f"{scope}:{user_id}", limit, window):
        raise HTTPException(429, "rate_limited")
