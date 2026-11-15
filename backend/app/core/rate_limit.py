"""In-process sliding-window rate limit for authentication routes.

A single Uvicorn worker is the expected local and small-deployment setup.
A later phase can swap this for a shared store without changing the routes.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.exceptions import AppException
from app.core.request_meta import client_ip


class RateLimiter:
    """Fixed-window counter keyed by bucket and client address."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def reset(self) -> None:
        """Drop all counters. Used by tests."""
        with self._lock:
            self._hits.clear()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        """Record one hit or raise when the caller is over the limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                raise AppException(
                    429,
                    "RATE_LIMITED",
                    "Too many requests. Try again shortly.",
                )
            hits.append(now)


limiter = RateLimiter()


def rate_limit(bucket: str, limit: int, window_seconds: int):
    """Build a dependency that limits requests for one auth route."""

    def _dependency(request: Request) -> None:
        ip = client_ip(request) or "unknown"
        limiter.check(f"{bucket}:{ip}", limit, window_seconds)

    return _dependency
