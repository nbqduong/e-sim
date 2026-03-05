from __future__ import annotations

from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, Field


class DocumentBase(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(default="", max_length=16_384)


class DocumentCreateRequest(DocumentBase):
    pass


class DocumentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    content: str | None = Field(default=None, max_length=16_384)


class Document(DocumentBase):
    id: str
    user_id: str
    updated_at: str
    drive_file_id: str | None = None
    drive_file_url: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[Document]


class DriveSaveResponse(BaseModel):
    drive_file_id: str
    drive_file_url: str | None = None
