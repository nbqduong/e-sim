from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        title: str,
        description: str = "",
        content: str = "",
        metadata_json: dict | None = None,
    ) -> Project:
        if metadata_json is None:
            metadata_json = {}
        project = Project(
            user_id=user_id, 
            title=title, 
            description=description,
            content=content,
            metadata_json=metadata_json
        )
        self._session.add(project)
        await self._session.flush()
        return project

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
        content: str | None = None,
        metadata_json: dict | None = None,
    ) -> Project | None:
        project = await self.get(user_id=user_id, project_id=project_id)
        if project is None:
            return None
        if title is not None:
            project.title = title
        if description is not None:
            project.description = description
        if content is not None:
            project.content = content
        if metadata_json is None:
            pass
        else:
            project.metadata_json = metadata_json
        await self._session.flush()
        return project

    async def delete(self, *, user_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        project = await self.get(user_id=user_id, project_id=project_id)
        if project is None:
            return False
        await self._session.delete(project)
        await self._session.flush()
        return True
