from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, EmailStr


class OAuthToken(BaseModel):
    user_id: str
    email: EmailStr
    access_token: str
    refresh_token: str | None = None
    token_expiry: datetime | None = None
    scope: str | None = None
    id_token: str | None = None

    def update_from_credentials(self, credentials: Any) -> "OAuthToken":
        scopes = " ".join(credentials.scopes) if getattr(credentials, "scopes", None) else self.scope
        return self.model_copy(
            update={
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token or self.refresh_token,
                "token_expiry": credentials.expiry,
                "scope": scopes,
                "id_token": credentials.id_token or self.id_token,
            }
        )


class AuthUrlResponse(BaseModel):
    auth_url: AnyHttpUrl
    state_ttl_seconds: int


class AuthResult(BaseModel):
    session_token: str
    user_id: str
    email: EmailStr
    expires_in: int
