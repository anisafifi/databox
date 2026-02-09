import asyncio
import time
import uuid
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RateLimitConfig:
    limit: int
    window_seconds: int = 60


class InMemoryRateLimiter:
    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._lock = asyncio.Lock()
        self._hits: dict[str, list[float]] = {}

    async def check(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        window_start = now - self._config.window_seconds
        async with self._lock:
            timestamps = [ts for ts in self._hits.get(key, []) if ts > window_start]
            if len(timestamps) >= self._config.limit:
                retry_after = int(max(1, self._config.window_seconds - (now - timestamps[0])))
                self._hits[key] = timestamps
                return False, retry_after
            timestamps.append(now)
            self._hits[key] = timestamps
            return True, 0


def _get_client_key(request: Request) -> str:
    auth_header = request.headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    client_host = request.client.host if request.client else "unknown"
    return f"anon:{client_host}"


def _ensure_request_id(request: Request) -> str:
    request_id = request.headers.get("x-request-id")
    if request_id:
        return request_id
    return f"db_{uuid.uuid4()}"


class RequestIdAndRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: InMemoryRateLimiter) -> None:
        super().__init__(app)
        self._limiter = limiter

    async def dispatch(self, request: Request, call_next):
        request_id = _ensure_request_id(request)
        request.state.request_id = request_id

        if request.url.path.startswith("/v1"):
            key = _get_client_key(request)
            allowed, retry_after = await self._limiter.check(key)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after), "X-Request-Id": request_id},
                )

        response = await call_next(request)
        response.headers.setdefault("X-Request-Id", request_id)
        return response
