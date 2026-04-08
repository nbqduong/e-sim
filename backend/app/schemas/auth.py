from __future__ import annotations

from pydantic import BaseModel, EmailStr


class AuthResult(BaseModel):
    session_token: str
    user_id: str
    email: EmailStr
    expires_in: int
