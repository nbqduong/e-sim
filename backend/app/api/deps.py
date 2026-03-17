from __future__ import annotations

from functools import lru_cache

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.repositories.document_repo import DocumentRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.services.google_drive import GoogleDriveService
from app.services.google_oauth import GoogleOAuthService
from app.services.session_manager import InvalidSessionError, SessionData, SessionManager
from app.utils.state_cache import StateCache


@lru_cache(maxsize=1)
def get_session_manager() -> SessionManager:
    return SessionManager(secret=settings.session_secret, ttl_seconds=settings.session_ttl_seconds)


@lru_cache(maxsize=1)
def get_state_cache() -> StateCache:
    return StateCache(ttl_seconds=settings.state_ttl_seconds)


def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_project_repo(db: AsyncSession = Depends(get_db)) -> ProjectRepository:
    return ProjectRepository(db)


def get_document_repo(db: AsyncSession = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)


def get_google_oauth_service(
    user_repo: UserRepository = Depends(get_user_repo),
    session_manager: SessionManager = Depends(get_session_manager),
    state_cache: StateCache = Depends(get_state_cache),
) -> GoogleOAuthService:
    return GoogleOAuthService(
        settings=settings,
        user_repo=user_repo,
        session_manager=session_manager,
        state_cache=state_cache,
    )


def get_google_drive_service(
    user_repo: UserRepository = Depends(get_user_repo),
) -> GoogleDriveService:
    return GoogleDriveService(settings=settings, user_repo=user_repo)


def get_current_user(
    x_session_token: str | None = Header(None, alias="X-Session-Token"),
    session_token: str | None = Cookie(None),
    session_manager: SessionManager = Depends(get_session_manager),
) -> SessionData:
    token = x_session_token or session_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session token",
        )
    try:
        return session_manager.verify(token)
    except InvalidSessionError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
