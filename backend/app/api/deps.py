from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status

from app.core.config import settings
from app.services.google_drive import GoogleDriveService
from app.services.google_oauth import GoogleOAuthService
from app.services.session_manager import InvalidSessionError, SessionData, SessionManager
from app.storage.document_store import DocumentStore
from app.storage.token_store import TokenStore
from app.utils.state_cache import StateCache


@lru_cache(maxsize=1)
def get_token_store() -> TokenStore:
    settings.ensure_data_dir()
    return TokenStore(settings.data_dir / "tokens.json")


@lru_cache(maxsize=1)
def get_document_store() -> DocumentStore:
    settings.ensure_data_dir()
    return DocumentStore(settings.data_dir / "documents.json")


@lru_cache(maxsize=1)
def get_session_manager() -> SessionManager:
    return SessionManager(secret=settings.session_secret, ttl_seconds=settings.session_ttl_seconds)


@lru_cache(maxsize=1)
def get_state_cache() -> StateCache:
    return StateCache(ttl_seconds=settings.state_ttl_seconds)


def get_google_oauth_service(
    token_store: TokenStore = Depends(get_token_store),
    session_manager: SessionManager = Depends(get_session_manager),
    state_cache: StateCache = Depends(get_state_cache),
) -> GoogleOAuthService:
    # If this function is called directly (outside FastAPI DI), the
    # default parameters will be `Depends` placeholder objects. Detect
    # that and construct the actual dependencies so callers can invoke
    # this helper directly in scripts/tests without relying on the
    # framework to resolve nested dependencies.
    if not hasattr(token_store, "save"):
        token_store = get_token_store()
    if not hasattr(session_manager, "issue"):
        session_manager = get_session_manager()
    if not hasattr(state_cache, "issue"):
        state_cache = get_state_cache()

    return GoogleOAuthService(
        settings=settings,
        token_store=token_store,
        session_manager=session_manager,
        state_cache=state_cache,
    )


def get_google_drive_service(
    token_store: TokenStore = Depends(get_token_store),
) -> GoogleDriveService:
    return GoogleDriveService(settings=settings, token_store=token_store)


def get_current_user(
    session_token: str = Header(..., alias="X-Session-Token"),
    session_manager: SessionManager = Depends(get_session_manager),
) -> SessionData:
    try:
        return session_manager.verify(session_token)
    except InvalidSessionError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
