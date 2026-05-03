from __future__ import annotations

import json
import secrets
from typing import Any

import redis.asyncio as aioredis


class StateCache:
    """Redis-backed store that tracks short-lived OAuth state tokens."""

    _CONSUME_SCRIPT = """
    local payload = redis.call("GET", KEYS[1])
    if payload then
        redis.call("DEL", KEYS[1])
    end
    return payload
    """

    def __init__(
        self,
        *,
        redis_url: str,
        ttl_seconds: int = 300,
        key_prefix: str = "oauth:state",
    ) -> None:
        self._redis: aioredis.Redis = aioredis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = max(1, ttl_seconds)
        self._key_prefix = key_prefix.strip(":")

    def _key(self, token: str) -> str:
        return f"{self._key_prefix}:{token}"

    async def issue(self, payload: Any = True, token: str | None = None) -> str:
        token = token or secrets.token_urlsafe(32)
        await self._redis.set(self._key(token), json.dumps(payload), ex=self._ttl_seconds)
        return token

    async def validate(self, token: str) -> bool:
        return bool(await self._redis.exists(self._key(token)))

    async def get(self, token: str) -> Any | None:
        payload = await self._redis.get(self._key(token))
        return self._decode_payload(payload)

    async def consume(self, token: str) -> None:
        await self._redis.delete(self._key(token))

    async def consume_payload(self, token: str) -> Any | None:
        payload = await self._redis.eval(self._CONSUME_SCRIPT, 1, self._key(token))
        return self._decode_payload(payload)

    async def close(self) -> None:
        await self._redis.aclose()

    @staticmethod
    def _decode_payload(payload: str | None) -> Any | None:
        if payload is None:
            return None
        return json.loads(payload)
