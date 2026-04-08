from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse

from app.api.deps import get_google_oauth_service, get_current_user
from app.services.session_manager import SessionData
from app.core.config import settings
from app.services.google_oauth import (
    GoogleOAuthService,
    OAuthConfigurationError,
    OAuthExchangeError,
    OAuthStateError,
)

import logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

@router.get("/google/login")
async def login_with_google(
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
):
    try:
        login_url = oauth_service.build_login_url()
    except OAuthConfigurationError as exc:  # pragma: no cover - configuration guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return RedirectResponse(url=login_url)


@router.get("/google/callback")
async def google_callback(
    state: str,
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    frontend_url = settings.frontend_url.rstrip("/")
    if error or not code:
        return RedirectResponse(f"{frontend_url}/demoui/not-authorized")

    try:
        auth_result = await oauth_service.exchange_code(code=code, state=state)

        frontend_url = settings.frontend_url.rstrip("/")
        response = RedirectResponse(f"{frontend_url}/demoui/home", status_code=303)
        
        logger.info(f"Setting cookie session_token={auth_result.session_token[:10]}...")
        
        response.set_cookie(
            key="session_token",
            value=auth_result.session_token,
            httponly=True,
            max_age=settings.session_ttl_seconds,
            samesite="lax",
            secure=True,
            path="/"
        )
        return response
    except (OAuthStateError, OAuthExchangeError) as exc:
        logger.error(f"OAuth Exchange/State Failed: {repr(exc)}")
        return RedirectResponse(f"{frontend_url}/demoui/not-authorized")
    except OAuthConfigurationError as exc:  # pragma: no cover - configuration guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

@router.get("/me", response_model=SessionData)
async def get_current_session(current_user: SessionData = Depends(get_current_user)):
    return current_user

@router.post("/logout")
async def logout():
    response = JSONResponse(content={"detail": "Logged out"})
    response.delete_cookie("session_token", path="/")
    return response
