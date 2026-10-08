"""A small in-memory rate limiter.

It counts calls per key (usually the visitor's IP address) inside a sliding
time window. The counts live in this process's memory, which is fine for one
small server: they reset when the server restarts, and they are not shared
between several server processes. That is an honest limit of this approach.
"""
import math
import threading
import time
from collections import deque

_all_limiters = []


class RateLimiter:
    def __init__(self, max_calls, window_seconds, clock=time.monotonic):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._clock = clock
        self._calls = {}  # key -> deque of timestamps
        self._lock = threading.Lock()
        _all_limiters.append(self)

    def check(self, key="everyone"):
        """Count one call for `key`.

        Returns None if the call is allowed, or the number of seconds to wait
        before trying again if the limit has been reached. A refused call is
        not counted.
        """
        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            calls = self._calls.setdefault(key, deque())
            while calls and calls[0] <= cutoff:
                calls.popleft()

            if len(calls) >= self.max_calls:
                return max(1, math.ceil(calls[0] + self.window_seconds - now))

            calls.append(now)
            self._forget_idle_keys(cutoff)
            return None

    def _forget_idle_keys(self, cutoff):
        # Keeps memory bounded: drop visitors whose calls have all expired.
        if len(self._calls) < 1000:
            return
        for key in [k for k, v in self._calls.items() if not v or v[-1] <= cutoff]:
            del self._calls[key]

    def reset(self):
        with self._lock:
            self._calls.clear()


def reset_all():
    """Forget every count. Used by the tests so they don't affect each other."""
    for limiter in _all_limiters:
        limiter.reset()


def client_ip(request):
    """The visitor's address.

    Behind a proxy (Vercel, Render) the real address is the first entry of the
    X-Forwarded-For header; request.client would just be the proxy.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def rate_limit(limiter, message="Too many requests. Please slow down.", per_client=True):
    """A FastAPI dependency that answers 429 when `limiter` says no.

        @app.post("/login", dependencies=[Depends(rate_limit(login_limit))])

    per_client=False counts every visitor together (a global cap).
    """
    from fastapi import HTTPException, Request

    def dependency(request: Request):
        key = client_ip(request) if per_client else "everyone"
        retry_after = limiter.check(key)
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail=message,
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
