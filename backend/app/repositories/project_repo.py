from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.user import User


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: uuid.UUID | None = None,
        user_id: uuid.UUID,
        title: str,
        description: str = "",
        metadata_json: dict | None = None,
        content_uri: str | None = None,
        content_checksum: str | None = None,
        content_updated_at: datetime | None = None,
        content_size_bytes: int | None = None,
    ) -> Project:
        if metadata_json is None:
            metadata_json = {}
        project_kwargs: dict[str, object] = {
            "user_id": user_id,
            "title": title,
            "description": description,
            "metadata_json": metadata_json,
            "content_uri": content_uri,
            "content_checksum": content_checksum,
            "content_updated_at": content_updated_at,
            "content_size_bytes": content_size_bytes,
        }
        if project_id is not None:
            project_kwargs["id"] = project_id
        project = Project(**project_kwargs)
        self._session.add(project)
        await self._session.flush()
        user = await self._session.get(User, user_id)
        if user is not None:
            user.project_count += 1
            await self._session.flush()
        hydrated_project = await self.get(user_id=user_id, project_id=project.id)
        if hydrated_project is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Created project could not be reloaded")
        return hydrated_project

    async def list_for_user(self, user_id: uuid.UUID) -> list[Project]:
        result = await self._session.execute(
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, *, user_id: uuid.UUID, project_id: uuid.UUID) -> Project | None:
        result = await self._session.execute(
            select(Project)
            .where(Project.id == project_id, Project.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        *,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        metadata_json: dict | None = None,
        content_uri: str | None = None,
        content_checksum: str | None = None,
        content_updated_at: datetime | None = None,
        content_size_bytes: int | None = None,
    ) -> Project | None:
        project = await self.get(user_id=user_id, project_id=project_id)
        if project is None:
            return None
        if title is not None:
            project.title = title
        if description is not None:
            project.description = description
        if metadata_json is None:
            pass
        else:
            project.metadata_json = metadata_json
        if content_uri is not None:
            project.content_uri = content_uri
        if content_checksum is not None:
            project.content_checksum = content_checksum
        if content_updated_at is not None:
            project.content_updated_at = content_updated_at
        if content_size_bytes is not None:
            project.content_size_bytes = content_size_bytes
        await self._session.flush()
        hydrated_project = await self.get(user_id=user_id, project_id=project.id)
        if hydrated_project is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Updated project could not be reloaded")
        return hydrated_project

    async def delete(self, *, user_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        project = await self.get(user_id=user_id, project_id=project_id)
        if project is None:
            return False
        await self._session.delete(project)
        await self._session.flush()
        user = await self._session.get(User, user_id)
        if user is not None and user.project_count > 0:
            user.project_count -= 1
            await self._session.flush()
        return True
