from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field


class DocumentBase(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(default="", max_length=16_384)


class DocumentCreateRequest(DocumentBase):
    project_id: UUID
    drive_file_id: str | None = None


class DocumentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    content: str | None = Field(default=None, max_length=16_384)


class DocumentResponse(DocumentBase):
    id: UUID
    project_id: UUID
    user_id: UUID
    drive_file_id: str | None = None
    drive_file_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Backward-compat alias
Document = DocumentResponse


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class DriveSaveResponse(BaseModel):
    drive_file_id: str
    drive_file_url: str | None = None
