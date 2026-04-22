"""HTTP middleware: correlation id, rate limit, access log.

Rate limiting is an in-memory fixed-window counter (60 requests / 60
seconds per client IP). This is sufficient for a single-process demo
deployment; production would front the API with a platform rate limiter
(Vercel, Cloudflare, nginx) and remove this middleware.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from asciip_shared import (
    CORRELATION_ID_HEADER,
    bind_correlation_id,
    get_logger,
    new_correlation_id,
)
from asciip_shared.correlation import reset_correlation_id
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import ORJSONResponse

# --------------------------------------------------------------------- rate-limit


@dataclass
class _Bucket:
    window_seconds: float
    capacity: int
    hits: deque[float] = field(default_factory=deque)

    def allow(self, now: float) -> bool:
        cutoff = now - self.window_seconds
        while self.hits and self.hits[0] < cutoff:
            self.hits.popleft()
        if len(self.hits) >= self.capacity:
            return False
        self.hits.append(now)
        return True

    def reset_in(self, now: float) -> float:
        if not self.hits:
            return 0.0
        return max(0.0, self.hits[0] + self.window_seconds - now)


class RateLimiter:
    def __init__(self, *, capacity: int = 60, window_seconds: float = 60.0) -> None:
        self.capacity = capacity
        self.window_seconds = window_seconds
        self._buckets: dict[str, _Bucket] = {}

    def check(self, key: str) -> tuple[bool, float]:
        bucket = self._buckets.setdefault(
            key, _Bucket(window_seconds=self.window_seconds, capacity=self.capacity)
        )
        now = time.monotonic()
        allowed = bucket.allow(now)
        return allowed, bucket.reset_in(now)


# --------------------------------------------------------------------- installers


def install_correlation_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def _correlation(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        inbound = request.headers.get(CORRELATION_ID_HEADER) or new_correlation_id()
        token = bind_correlation_id(inbound)
        try:
            response = await call_next(request)
        finally:
            reset_correlation_id(token)
        response.headers[CORRELATION_ID_HEADER] = inbound
        return response


def install_access_log_middleware(app: FastAPI) -> None:
    log = get_logger("asciip.api.access")

    @app.middleware("http")
    async def _access(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=round(elapsed_ms, 2),
            client=request.client.host if request.client else "unknown",
        )
        response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.2f}"
        return response


def install_rate_limit_middleware(
    app: FastAPI, *, capacity: int = 60, window_seconds: float = 60.0
) -> None:
    limiter = RateLimiter(capacity=capacity, window_seconds=window_seconds)
    app.state.rate_limiter = limiter

    @app.middleware("http")
    async def _limit(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Bypass for meta/docs/OpenAPI routes.
        if request.url.path.startswith(
            ("/api/health", "/api/version", "/api/docs", "/api/redoc", "/api/openapi")
        ):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        allowed, retry_in = limiter.check(client)
        if not allowed:
            return ORJSONResponse(
                {
                    "type": "urn:asciip:error:rate-limit",
                    "title": "Rate limit exceeded",
                    "status": status.HTTP_429_TOO_MANY_REQUESTS,
                    "detail": f"Try again in {retry_in:.1f}s",
                },
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Content-Type": "application/problem+json",
                    "Retry-After": str(int(retry_in) + 1),
                },
            )
        return await call_next(request)
