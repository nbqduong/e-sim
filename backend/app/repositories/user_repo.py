from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

DEFAULT_ADMIN_EMAIL = "nbqduong@gmail.com"


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_google_sub(self, google_sub: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.google_sub == google_sub)
        )
        return result.scalar_one_or_none()

    async def get_or_create_by_google_sub(
        self,
        *,
        google_sub: str,
        email: str,
        display_name: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expiry: datetime | None = None,
        token_scope: str | None = None,
        id_token: str | None = None,
    ) -> User:
        user = await self.get_by_google_sub(google_sub)
        should_be_default_admin = email.strip().lower() == DEFAULT_ADMIN_EMAIL
        if user is None:
            user = User(
                google_sub=google_sub,
                email=email,
                display_name=display_name,
                is_admin=should_be_default_admin,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=token_expiry,
                token_scope=token_scope,
                id_token=id_token,
            )
            self._session.add(user)
        else:
            # Update tokens on every login
            user.email = email
            user.is_admin = user.is_admin or should_be_default_admin
            if display_name:
                user.display_name = display_name
            user.access_token = access_token
            if refresh_token:
                user.refresh_token = refresh_token
            user.token_expiry = token_expiry
            user.token_scope = token_scope
            user.id_token = id_token
        await self._session.flush()
        return user

    async def update_tokens(
        self,
        user_id: uuid.UUID,
        *,
        access_token: str,
        refresh_token: str | None = None,
        token_expiry: datetime | None = None,
        token_scope: str | None = None,
        id_token: str | None = None,
    ) -> User | None:
        user = await self.get_by_id(user_id)
        if user is None:
            return None
        user.access_token = access_token
        if refresh_token:
            user.refresh_token = refresh_token
        user.token_expiry = token_expiry
        if token_scope:
            user.token_scope = token_scope
        if id_token:
            user.id_token = id_token
        await self._session.flush()
        return user

    async def add_balance(self, user_id: uuid.UUID, amount_cents: int) -> User | None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(balance=User.balance + amount_cents)
            .returning(User)
        )
        result = await self._session.execute(stmt)
        updated_user = result.scalar_one_or_none()
        await self._session.flush()
        return updated_user
        
    async def deduct_balance(self, user_id: uuid.UUID, amount_cents: int) -> User | None:
        stmt = (
            update(User)
            .where(User.id == user_id, User.balance >= amount_cents)
            .values(balance=User.balance - amount_cents)
            .returning(User)
        )
        result = await self._session.execute(stmt)
        updated_user = result.scalar_one_or_none()
        await self._session.flush()
        return updated_user
