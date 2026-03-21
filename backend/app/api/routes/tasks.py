from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_task_repo
from app.repositories.task_repo import TaskRepository
from app.schemas.task import TaskResponse, TaskListResponse
from app.services.session_manager import SessionData

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    current_user: SessionData = Depends(get_current_user),
    task_repo: TaskRepository = Depends(get_task_repo),
) -> TaskListResponse:
    tasks = await task_repo.list_for_user(user_id=uuid.UUID(current_user.user_id))
    return TaskListResponse(tasks=[TaskResponse.model_validate(t) for t in tasks])


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    current_user: SessionData = Depends(get_current_user),
    task_repo: TaskRepository = Depends(get_task_repo),
) -> TaskResponse:
    task = await task_repo.get(task_id=task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if str(task.user_id) != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return TaskResponse.model_validate(task)
