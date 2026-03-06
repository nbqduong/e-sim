from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, EmailStr


class InvalidSessionError(RuntimeError):
    """Raised when a provided session token cannot be validated."""


class SessionData(BaseModel):
    user_id: str
    email: EmailStr


class SessionManager:
    def __init__(self, *, secret: str, ttl_seconds: int) -> None:
        self._serializer = URLSafeTimedSerializer(secret_key=secret, salt="session-token")
        self._ttl_seconds = ttl_seconds

    def issue(self, user_id: str, email: str) -> str:
        payload = SessionData(user_id=user_id, email=email)
        return self._serializer.dumps(payload.model_dump())

    def verify(self, token: str) -> SessionData:
        try:
            payload = self._serializer.loads(token, max_age=self._ttl_seconds)
            return SessionData(**payload)
        except SignatureExpired as exc:  # pragma: no cover - defensive guard
            raise InvalidSessionError("Session expired") from exc
        except BadSignature as exc:  # pragma: no cover - defensive guard
            raise InvalidSessionError("Invalid session token") from exc
