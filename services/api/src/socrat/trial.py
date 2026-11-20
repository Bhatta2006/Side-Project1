"""Per-visitor request limits for the signed-out endpoints (email sign-in).

``visitor`` is a salted hash of the address our own proxy saw, never stored; ``allow`` is an
hourly cap kept in memory per API process (with several processes the caps multiply).
"""

import hashlib
import time
from collections import defaultdict, deque

from fastapi import Request

_recent: dict[str, deque[float]] = defaultdict(deque)


def visitor(request: Request) -> str:
    """A salted hash of the address our own proxy saw; never stored.

    The rightmost X-Forwarded-For entry is the one the web server appended, so a client
    cannot pick it by sending its own header (earlier entries are client-controlled).
    """
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[-1].strip()
    address = forwarded or (request.client.host if request.client else "unknown")
    salt = request.app.state.settings.session_secret.get_secret_value()
    return hashlib.sha256(f"{salt}:{address}".encode()).hexdigest()[:32]


def allow(key: str, per_hour: int, stamp: float | None = None) -> bool:
    stamp = time.time() if stamp is None else stamp
    window = _recent[key]
    while window and window[0] <= stamp - 3600:
        window.popleft()
    if len(window) >= per_hour:
        return False
    window.append(stamp)
    if len(_recent) > 50_000:  # forget idle visitors so memory stays bounded
        for stale in [k for k, v in _recent.items() if not v or v[-1] <= stamp - 3600]:
            del _recent[stale]
    return True
