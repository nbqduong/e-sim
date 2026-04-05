from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, AnyUrl


class TaskResponse(BaseModel):
    id: UUID
    user_id: UUID
    document_id: UUID | None = None
    task_type: str
    status: str
    result_url: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
