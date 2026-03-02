from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_google_oauth_service
from app.core.config import settings
from app.schemas.auth import AuthResult, AuthUrlResponse
from app.services.google_oauth import (
    GoogleOAuthService,
    OAuthConfigurationError,
    OAuthExchangeError,
    OAuthStateError,
)

router = APIRouter(prefix="/google", tags=["auth"])


@router.get("/login", response_model=AuthUrlResponse)
async def login_with_google(
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
) -> AuthUrlResponse:
    try:
        login_url = oauth_service.build_login_url()
    except OAuthConfigurationError as exc:  # pragma: no cover - configuration guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return AuthUrlResponse(auth_url=login_url, state_ttl_seconds=settings.state_ttl_seconds)


@router.get("/callback", response_model=AuthResult)
async def google_callback(
    code: str,
    state: str,
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
) -> AuthResult:
    try:
        return oauth_service.exchange_code(code=code, state=state)
    except OAuthStateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except OAuthConfigurationError as exc:  # pragma: no cover - configuration guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except OAuthExchangeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
