from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

from app.core.config import Settings
from app.schemas.auth import AuthResult
from app.services.session_manager import SessionManager
from app.repositories.user_repo import UserRepository
from app.utils.state_cache import StateCache

logger = logging.getLogger(__name__)


class OAuthConfigurationError(RuntimeError):
    pass


class OAuthStateError(RuntimeError):
    pass


class OAuthExchangeError(RuntimeError):
    pass


class GoogleOAuthService:
    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    def __init__(
        self,
        *,
        settings: Settings,
        user_repo: UserRepository,
        session_manager: SessionManager,
        state_cache: StateCache,
    ) -> None:
        self._settings = settings
        self._user_repo = user_repo
        self._session_manager = session_manager
        self._state_cache = state_cache

    def build_login_url(self) -> str:
        self._ensure_credentials()
        flow = self._build_flow()
        authorization_url, state = flow.authorization_url()
        self._state_cache.issue({"code_verifier": flow.code_verifier}, token=state)
        
        logger.info(f"Built Google OAuth redirect URI: {self._settings.google_redirect_uri}")
        logger.info(f"Final Authorization URL sent to user: {authorization_url}")
        
        return authorization_url

    async def exchange_code(self, *, code: str, state: str) -> AuthResult:
        self._ensure_credentials()
        state_payload = self._state_cache.get(state)
        if state_payload is None:
            raise OAuthStateError("OAuth state token is invalid or expired")
        self._state_cache.consume(state)

        flow = self._build_flow()
        code_verifier = state_payload.get("code_verifier") if isinstance(state_payload, dict) else None
        try:
            await asyncio.to_thread(self._fetch_credentials, flow, code, code_verifier)
        except Exception as exc:  # pragma: no cover - network interaction
            logger.exception("Google OAuth code exchange failed")
            raise OAuthExchangeError("Unable to exchange authorization code") from exc

        credentials = flow.credentials
        profile = await asyncio.to_thread(self._extract_profile, credentials.id_token)

        # Create or update user in the database
        user = await self._user_repo.get_or_create_by_google_sub(
            google_sub=profile["sub"],
            email=profile["email"],
            display_name=profile.get("name"),
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_expiry=credentials.expiry,
            token_scope=" ".join(credentials.scopes or []),
            id_token=credentials.id_token,
        )

        session_token = self._session_manager.issue(
            user_id=str(user.id), email=user.email
        )

        expires_in = self._calculate_expires_in(credentials.expiry)
        return AuthResult(
            session_token=session_token,
            user_id=str(user.id),
            email=user.email,
            expires_in=expires_in,
        )

    def _fetch_credentials(self, flow: Flow, code: str, code_verifier: str | None) -> None:
        if code_verifier:
            flow.fetch_token(code=code, code_verifier=code_verifier)
        else:
            flow.fetch_token(code=code)

    def _build_flow(self) -> Flow:
        client_config: dict[str, Any] = {
            "web": {
                "client_id": self._settings.google_client_id,
                "client_secret": self._settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self._settings.google_redirect_uri],
            }
        }
        flow = Flow.from_client_config(client_config, scopes=self.SCOPES)
        flow.redirect_uri = self._settings.google_redirect_uri
        return flow

    def _extract_profile(self, raw_id_token: str | None) -> dict[str, Any]:
        if not raw_id_token:
            raise OAuthExchangeError("Missing id_token in OAuth response")
        request = Request()
        return id_token.verify_oauth2_token(raw_id_token, request, self._settings.google_client_id)

    def _calculate_expires_in(self, expiry: datetime | None) -> int:
        if expiry is None:
            return self._settings.session_ttl_seconds
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        delta = int(max((expiry - now).total_seconds(), 0))
        return delta or self._settings.session_ttl_seconds

    def _ensure_credentials(self) -> None:
        if not self._settings.google_client_id or not self._settings.google_client_secret:
            raise OAuthConfigurationError("Google OAuth credentials are not configured")
