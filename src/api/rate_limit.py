import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, status

REGULATION_LIMIT = 10  # requests per minute per user
VERIFY_LIMIT = 30  # requests per minute per client address
WINDOW_SECONDS = 60.0


class RateLimiter:
    """Sliding-window limiter. In-process, so it assumes a single API instance
    (the Railway free tier). Redis is not permitted (CONSTRAINTS.md)."""

    def __init__(
        self,
        limit: int,
        window_seconds: float = WINDOW_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> float | None:
        """Record a hit. Returns None if allowed, else seconds until it would be."""
        now = self._clock()
        hits = self._hits[key]
        while hits and now - hits[0] >= self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return self._window - (now - hits[0])
        hits.append(now)
        return None

    def reset(self) -> None:
        self._hits.clear()


def _too_many(retry_after: float) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Please wait a moment and try again.",
        headers={"Retry-After": str(max(1, int(retry_after) + 1))},
    )


regulation_limiter = RateLimiter(REGULATION_LIMIT)
verify_limiter = RateLimiter(VERIFY_LIMIT)


def limit_regulations(user: dict[str, Any]) -> None:
    """Per authenticated user. Runs after authentication so the key is a real
    user, not a header an attacker can vary."""
    retry = regulation_limiter.check(str(user["id"]))
    if retry is not None:
        raise _too_many(retry)


def client_address(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def limit_verify(request: Request) -> None:
    """Per client address, for the unauthenticated certificate check."""
    retry = verify_limiter.check(client_address(request))
    if retry is not None:
        raise _too_many(retry)
