from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        task_type: str,
        document_id: uuid.UUID | None = None,
    ) -> Task:
        task = Task(user_id=user_id, task_type=task_type, document_id=document_id)
        self._session.add(task)
        await self._session.flush()
        return task

    async def get(self, *, task_id: uuid.UUID) -> Task | None:
        result = await self._session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def list_for_user(self, *, user_id: uuid.UUID) -> list[Task]:
        result = await self._session.execute(
            select(Task).where(Task.user_id == user_id).order_by(Task.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        *,
        task_id: uuid.UUID,
        status: str,
        result_url: str | None = None,
        error: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> Task | None:
        task = await self.get(task_id=task_id)
        if task is None:
            return None
        task.status = status
        if result_url is not None:
            task.result_url = result_url
        if error is not None:
            task.error = error
        if started_at is not None:
            task.started_at = started_at
        if finished_at is not None:
            task.finished_at = finished_at
        await self._session.flush()
        return task
