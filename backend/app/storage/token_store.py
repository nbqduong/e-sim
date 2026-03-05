from __future__ import annotations

from pathlib import Path

from app.schemas.auth import OAuthToken
from app.storage.json_store import JsonStore


class TokenStore(JsonStore):
    def __init__(self, path: Path) -> None:
        super().__init__(path)

    def save(self, token: OAuthToken) -> None:
        data = self._read()
        data[token.user_id] = token.model_dump(mode="json")
        self._write(data)

    def get(self, user_id: str) -> OAuthToken | None:
        data = self._read()
        raw = data.get(user_id)
        if not raw:
            return None
        return OAuthToken(**raw)
