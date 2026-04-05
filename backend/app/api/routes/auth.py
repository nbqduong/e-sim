from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.api.deps import get_google_oauth_service
from app.core.config import settings
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
    state: str,
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error or not code:
        return RedirectResponse("/not-authorized")

    try:
        auth_result = await oauth_service.exchange_code(code=code, state=state)

        response = RedirectResponse("/documents")
        response.set_cookie(
            key="session_token",
            value=auth_result.session_token,
            httponly=True,
            max_age=settings.session_ttl_seconds,
            samesite="lax",
            secure=settings.session_cookie_secure,
        )
        return response
    except (OAuthStateError, OAuthExchangeError):
        return RedirectResponse("/not-authorized")
    except OAuthConfigurationError as exc:  # pragma: no cover - configuration guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
