from __future__ import annotations

import time

import redis.asyncio as aioredis


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
    key = f"rate_limit:{namespace}:{user_id}:{project_id}"
    now = time.time()
    window_start = now - window_seconds

    client: aioredis.Redis = aioredis.from_url(redis_url, decode_responses=False)
    try:
        async with client.pipeline(transaction=True) as pipe:
            # Remove entries outside the current window
            pipe.zremrangebyscore(key, "-inf", window_start)
            # Count remaining entries
            pipe.zcard(key)
            # Record this request
            pipe.zadd(key, {f"{now}": now})
            # Reset TTL so idle keys expire
            pipe.expire(key, window_seconds)
            results = await pipe.execute()

        current_count: int = results[1]
        return current_count < max_requests
    finally:
        await client.aclose()
