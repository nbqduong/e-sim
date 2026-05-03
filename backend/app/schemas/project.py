from __future__ import annotations

from typing import Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    metadata_json: dict[str, Any] | None = Field(default=None)


class ProjectResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: str
    metadata_json: dict[str, Any]
    content_uri: str | None
    content_checksum: str | None
    content_updated_at: datetime | None
    content_size_bytes: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]


class SignedProjectUploadResponse(BaseModel):
    bucket_name: str
    content_length: int
    content_type: str
    max_upload_size_bytes: int
    method: str
    object_name: str
    signed_url_expiration_seconds: int
    storage_uri: str
    upload_url: str


class SignedProjectDownloadResponse(BaseModel):
    bucket_name: str
    method: str
    object_name: str
    signed_url_expiration_seconds: int
    storage_uri: str
    download_url: str


class ProjectSaveToCloudPrepareRequest(BaseModel):
    project_id: UUID | None = None
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    content_checksum: str = Field(min_length=1, max_length=128)
    content_length: int = Field(gt=0)
    content_type: str = Field(min_length=1, max_length=255)


class ProjectSaveToCloudPrepareResponse(BaseModel):
    project_id: UUID
    needs_upload: bool
    project: ProjectResponse | None = None
    upload: SignedProjectUploadResponse | None = None


class ProjectSaveToCloudCompleteRequest(BaseModel):
    project_id: UUID
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    content_checksum: str = Field(min_length=1, max_length=128)
    content_length: int = Field(gt=0)
    content_type: str = Field(min_length=1, max_length=255)


class ProjectSyncRequest(BaseModel):
    local_checksum: str | None = Field(default=None, max_length=128)


class ProjectSyncResponse(BaseModel):
    project: ProjectResponse
    needs_download: bool
    download: SignedProjectDownloadResponse | None = None
