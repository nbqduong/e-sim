from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
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


def _resolve_google_callback_url(request: Request) -> str:
    request_callback_url = str(request.url_for("google_callback"))
    configured_callback_url = settings.google_redirect_uri.strip()

    if configured_callback_url:
        if configured_callback_url != request_callback_url:
            logger.warning(
                "Google OAuth callback mismatch: configured=%s request_derived=%s host=%s "
                "x_forwarded_host=%s x_forwarded_proto=%s",
                configured_callback_url,
                request_callback_url,
                request.headers.get("host"),
                request.headers.get("x-forwarded-host"),
                request.headers.get("x-forwarded-proto"),
            )
        else:
            logger.info("Google OAuth callback resolved to %s", configured_callback_url)
        return configured_callback_url

    logger.info("Google OAuth callback resolved from request to %s", request_callback_url)
    return request_callback_url


@router.get("/google/login")
async def login_with_google(
    request: Request,
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
):
    try:
        callback_url = _resolve_google_callback_url(request)
        login_url = await oauth_service.build_login_url(redirect_uri=callback_url)
    except OAuthConfigurationError as exc:  # pragma: no cover - configuration guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return RedirectResponse(url=login_url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    state: str,
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error or not code:
        return RedirectResponse("/demoui/not-authorized", status_code=303)

    try:
        callback_url = _resolve_google_callback_url(request)
        auth_result = await oauth_service.exchange_code(
            code=code,
            state=state,
            redirect_uri=callback_url,
        )

        response = RedirectResponse("/demoui/home", status_code=303)
        
        logger.info(f"Setting cookie session_token={auth_result.session_token[:10]}...")
        
        response.set_cookie(
            key="session_token",
            value=auth_result.session_token,
            httponly=True,
            max_age=settings.session_ttl_seconds,
            samesite="lax",
            secure=settings.session_cookie_secure,
            path="/"
        )
        return response
    except (OAuthStateError, OAuthExchangeError) as exc:
        logger.error(f"OAuth Exchange/State Failed: {repr(exc)}")
        return RedirectResponse("/demoui/not-authorized", status_code=303)
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
