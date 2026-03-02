from __future__ import annotations

import secrets
from typing import Any

from cachetools import TTLCache


class StateCache:
    """Simple in-memory store that tracks short-lived OAuth state tokens."""

    def __init__(self, ttl_seconds: int = 300, max_tokens: int = 1024) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=max_tokens, ttl=ttl_seconds)

    def issue(self, payload: Any = True, token: str | None = None) -> str:
        token = token or secrets.token_urlsafe(32)
        self._cache[token] = payload
        return token

    def validate(self, token: str) -> bool:
        return token in self._cache

    def get(self, token: str) -> Any | None:
        return self._cache.get(token)

    def consume(self, token: str) -> None:
        self._cache.pop(token, None)
