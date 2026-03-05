from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

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


@router.get("/login")
async def login_with_google(
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
):
    try:
        login_url = oauth_service.build_login_url()
    except OAuthConfigurationError as exc:  # pragma: no cover - configuration guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return RedirectResponse(url=login_url)


@router.get("/callback")
async def google_callback(
    code: str,
    state: str,
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
) -> RedirectResponse:
    try:
        auth_result = oauth_service.exchange_code(code=code, state=state)

        response = RedirectResponse("/dashboard")
        response.set_cookie(
            key="session_token",
            value=auth_result.session_token,
            httponly=True,
            max_age=settings.session_ttl_seconds,
            samesite="lax",
            secure=False,  # Set to True in production with HTTPS
        )
        return response
    except OAuthStateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except OAuthConfigurationError as exc:  # pragma: no cover - configuration guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except OAuthExchangeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
