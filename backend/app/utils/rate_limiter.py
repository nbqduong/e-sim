from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Iterable

import redis.asyncio as aioredis
from redis.exceptions import RedisError
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    reset_after_seconds: int


class RedisSlidingWindowRateLimiter:
    """Redis-backed sliding-window rate limiter shared by API features."""

    _CHECK_SCRIPT = """
    redis.call("ZREMRANGEBYSCORE", KEYS[1], "-inf", ARGV[1])
    local current_count = redis.call("ZCARD", KEYS[1])
    local max_requests = tonumber(ARGV[3])
    local window_ms = tonumber(ARGV[4])

    if current_count >= max_requests then
        local oldest = redis.call("ZRANGE", KEYS[1], 0, 0, "WITHSCORES")
        local retry_after_ms = window_ms
        if oldest[2] then
            retry_after_ms = tonumber(oldest[2]) + window_ms - tonumber(ARGV[2])
            if retry_after_ms < 1 then
                retry_after_ms = 1
            end
        end
        return {0, current_count, retry_after_ms}
    end

    redis.call("ZADD", KEYS[1], ARGV[2], ARGV[5])
    redis.call("PEXPIRE", KEYS[1], window_ms)
    return {1, current_count + 1, window_ms}
    """

    def __init__(self, redis_url: str, *, key_prefix: str = "rate_limit") -> None:
        self._redis: aioredis.Redis = aioredis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix.strip(":")

    async def check(
        self,
        *,
        namespace: str,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> RateLimitResult:
        max_requests = max(1, max_requests)
        window_seconds = max(1, window_seconds)
        window_ms = window_seconds * 1000
        now_ms = time.time_ns() // 1_000_000
        window_start_ms = now_ms - window_ms
        key = self._key(namespace=namespace, identifier=identifier)
        member = f"{now_ms}:{time.time_ns()}"

        allowed_raw, count_raw, ttl_raw = await self._redis.eval(
            self._CHECK_SCRIPT,
            1,
            key,
            window_start_ms,
            now_ms,
            max_requests,
            window_ms,
            member,
        )

        count = int(count_raw)
        ttl_ms = max(0, int(ttl_raw))
        reset_after_seconds = max(1, math.ceil(ttl_ms / 1000))
        allowed = bool(int(allowed_raw))
        remaining = max(0, max_requests - count)

        return RateLimitResult(
            allowed=allowed,
            limit=max_requests,
            remaining=remaining,
            retry_after_seconds=0 if allowed else reset_after_seconds,
            reset_after_seconds=reset_after_seconds,
        )

    async def close(self) -> None:
        await self._redis.aclose()

    def _key(self, *, namespace: str, identifier: str) -> str:
        safe_namespace = namespace.strip(":") or "default"
        safe_identifier = identifier.replace(" ", "_")
        return f"{self._key_prefix}:{safe_namespace}:{safe_identifier}"


class GlobalRateLimitMiddleware:
    """Apply a coarse global per-client request limit before route handling."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        limiter: RedisSlidingWindowRateLimiter,
        max_requests: int,
        window_seconds: int,
        enabled: bool = True,
        fail_open: bool = True,
        exempt_path_prefixes: Iterable[str] = (),
        trust_proxy_headers: bool = True,
    ) -> None:
        self.app = app
        self.limiter = limiter
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.enabled = enabled
        self.fail_open = fail_open
        self.exempt_path_prefixes = tuple(prefix for prefix in exempt_path_prefixes if prefix)
        self.trust_proxy_headers = trust_proxy_headers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._should_limit(scope):
            await self.app(scope, receive, send)
            return

        identifier = self._client_identifier(scope)
        try:
            result = await self.limiter.check(
                namespace="global",
                identifier=identifier,
                max_requests=self.max_requests,
                window_seconds=self.window_seconds,
            )
        except RedisError:
            logger.exception("Global rate limit check failed for client %s", identifier)
            if self.fail_open:
                await self.app(scope, receive, send)
                return
            response = JSONResponse(
                {"detail": "Rate limiter unavailable"},
                status_code=503,
            )
            await response(scope, receive, send)
            return

        if not result.allowed:
            response = JSONResponse(
                {"detail": "Too many requests"},
                status_code=429,
                headers=self._rate_limit_headers(result, include_retry_after=True),
            )
            await response(scope, receive, send)
            return

        async def send_with_rate_limit_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    (name.lower().encode("latin-1"), value.encode("latin-1"))
                    for name, value in self._rate_limit_headers(result).items()
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_rate_limit_headers)

    def _should_limit(self, scope: Scope) -> bool:
        if scope["type"] != "http":
            return False
        if not self.enabled or self.max_requests <= 0 or self.window_seconds <= 0:
            return False
        if scope.get("method") == "OPTIONS":
            return False

        path = str(scope.get("path") or "/")
        return not any(path.startswith(prefix) for prefix in self.exempt_path_prefixes)

    def _client_identifier(self, scope: Scope) -> str:
        headers = self._headers(scope)

        if self.trust_proxy_headers:
            forwarded_for = headers.get("x-forwarded-for")
            if forwarded_for:
                first_hop = forwarded_for.split(",", 1)[0].strip()
                if first_hop:
                    return first_hop

            real_ip = headers.get("x-real-ip")
            if real_ip:
                return real_ip.strip()

        client = scope.get("client")
        if client:
            return str(client[0])
        return "unknown"

    @staticmethod
    def _headers(scope: Scope) -> dict[str, str]:
        return {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }

    @staticmethod
    def _rate_limit_headers(
        result: RateLimitResult,
        *,
        include_retry_after: bool = False,
    ) -> dict[str, str]:
        headers = {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(result.reset_after_seconds),
        }
        if include_retry_after:
            headers["Retry-After"] = str(result.retry_after_seconds)
        return headers


async def is_allowed(
    redis_url: str,
    user_id: str,
    project_id: str,
    max_requests: int,
    window_seconds: int,
    namespace: str = "signed_url",
) -> bool:
    """Check and record a rate-limited request using a Redis sorted-set sliding window.

    Opens a short-lived async Redis connection, runs an atomic pipeline, then closes.
    Returns True if the request is within the limit, False if the limit is exceeded.

    The sorted set key is ``rate_limit:{namespace}:{user_id}:{project_id}``.
    Members are scored by a monotonic timestamp (seconds) so old entries can be
    pruned cheaply with ZREMRANGEBYSCORE. TTL is set to ``window_seconds`` so
    stale keys are cleaned up automatically by Redis.
    """
    limiter = RedisSlidingWindowRateLimiter(redis_url)
    try:
        result = await limiter.check(
            namespace=namespace,
            identifier=f"{user_id}:{project_id}",
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
        return result.allowed
    finally:
        await limiter.close()
