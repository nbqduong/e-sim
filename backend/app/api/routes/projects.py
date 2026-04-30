from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_billing_manager, get_current_user, get_project_repo, get_user_repo
from app.core.config import settings
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectSaveToCloudCompleteRequest,
    ProjectSaveToCloudPrepareRequest,
    ProjectSaveToCloudPrepareResponse,
    ProjectSyncRequest,
    ProjectSyncResponse,
    ProjectUpdateRequest,
)
from app.services.blob_storage import (
    build_project_storage_uri,
    create_signed_project_download,
    create_signed_project_upload,
    delete_project_prefix,
)
from app.services.billing_manager import BillingManager, ProjectLimitExceededError
from app.services.session_manager import SessionData
from app.utils.rate_limiter import is_allowed as rate_limit_check

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _current_user_id(current_user: SessionData) -> uuid.UUID:
    return uuid.UUID(current_user.user_id)


def _translate_blob_storage_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    client_error_prefixes = (
        "content_length",
        "content_type",
        "Upload payload exceeds",
    )
    status_code = (
        status.HTTP_400_BAD_REQUEST
        if message.startswith(client_error_prefixes)
        else status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    return HTTPException(status_code=status_code, detail=message)


async def _enforce_project_creation_limit(
    *,
    user_id: uuid.UUID,
    user_repo: UserRepository,
    billing_manager: BillingManager,
) -> None:
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        billing_manager.ensure_can_create_project(
            billing_tier=user.billing_tier,
            project_count=user.project_count,
        )
    except ProjectLimitExceededError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


async def _enforce_project_creation_rate_limit(user_id: uuid.UUID) -> None:
    if not await rate_limit_check(
        settings.redis_url,
        str(user_id),
        "create",
        settings.project_create_rate_limit_max_requests,
        settings.project_create_rate_limit_window_seconds,
        namespace="project_create",
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded: max {settings.project_create_rate_limit_max_requests} "
                f"project creations per {settings.project_create_rate_limit_window_seconds}s."
            ),
        )


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> ProjectListResponse:
    projects = await project_repo.list_for_user(_current_user_id(current_user))
    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects]
    )


@router.post("/save-to-cloud/prepare", response_model=ProjectSaveToCloudPrepareResponse)
async def prepare_project_save_to_cloud(
    payload: ProjectSaveToCloudPrepareRequest,
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    billing_manager: BillingManager = Depends(get_billing_manager),
) -> ProjectSaveToCloudPrepareResponse:
    user_id = _current_user_id(current_user)
    existing_project = None

    if payload.project_id is not None:
        existing_project = await project_repo.get(user_id=user_id, project_id=payload.project_id)
        if existing_project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    else:
        await _enforce_project_creation_limit(
            user_id=user_id,
            user_repo=user_repo,
            billing_manager=billing_manager,
        )

    # Rate limit: max N signed upload URL generations per project per window
    target_project_id = existing_project.id if existing_project is not None else uuid.uuid4()
    if not await rate_limit_check(
        settings.redis_url,
        str(user_id),
        str(target_project_id),
        settings.storage_rate_limit_max_requests,
        settings.storage_rate_limit_window_seconds,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded: max {settings.storage_rate_limit_max_requests} "
                f"signed URL requests per {settings.storage_rate_limit_window_seconds}s per project."
            ),
        )

    if (
        existing_project is not None
        and existing_project.content_checksum is not None
        and existing_project.content_checksum == payload.content_checksum
    ):
        project = await project_repo.update(
            user_id=user_id,
            project_id=existing_project.id,
            title=payload.title,
            description=payload.description,
            metadata_json=payload.metadata_json,
        )
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return ProjectSaveToCloudPrepareResponse(
            project_id=project.id,
            needs_upload=False,
            project=ProjectResponse.model_validate(project),
        )

    try:
        upload_payload = create_signed_project_upload(
            settings,
            user_id=user_id,
            project_id=target_project_id,
            content_type=payload.content_type,
            content_length=payload.content_length,
        )
    except ValueError as exc:
        raise _translate_blob_storage_error(exc)
    return ProjectSaveToCloudPrepareResponse(
        project_id=target_project_id,
        needs_upload=True,
        project=ProjectResponse.model_validate(existing_project) if existing_project is not None else None,
        upload=upload_payload,
    )


@router.post("/save-to-cloud/complete", response_model=ProjectResponse)
async def complete_project_save_to_cloud(
    payload: ProjectSaveToCloudCompleteRequest,
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    billing_manager: BillingManager = Depends(get_billing_manager),
) -> ProjectResponse:
    user_id = _current_user_id(current_user)
    try:
        storage_uri = build_project_storage_uri(
            settings,
            user_id=user_id,
            project_id=payload.project_id,
        )
    except ValueError as exc:
        raise _translate_blob_storage_error(exc)
    synced_at = datetime.now(tz=timezone.utc)
    existing_project = await project_repo.get(user_id=user_id, project_id=payload.project_id)

    if existing_project is None:
        await _enforce_project_creation_rate_limit(user_id)
        await _enforce_project_creation_limit(
            user_id=user_id,
            user_repo=user_repo,
            billing_manager=billing_manager,
        )
        project = await project_repo.create(
            project_id=payload.project_id,
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            metadata_json=payload.metadata_json,
            content_uri=storage_uri,
            content_checksum=payload.content_checksum,
            content_updated_at=synced_at,
            content_size_bytes=payload.content_length,
        )
    else:
        project = await project_repo.update(
            user_id=user_id,
            project_id=payload.project_id,
            title=payload.title,
            description=payload.description,
            metadata_json=payload.metadata_json,
            content_uri=storage_uri,
            content_checksum=payload.content_checksum,
            content_updated_at=synced_at,
            content_size_bytes=payload.content_length,
        )
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> ProjectResponse:
    project = await project_repo.get(
        project_id=project_id, user_id=_current_user_id(current_user)
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/sync", response_model=ProjectSyncResponse)
async def sync_project(
    project_id: uuid.UUID,
    payload: ProjectSyncRequest,
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> ProjectSyncResponse:
    user_id = _current_user_id(current_user)
    project = await project_repo.get(project_id=project_id, user_id=user_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    needs_download = (
        project.content_uri is not None
        and project.content_checksum is not None
        and project.content_checksum != payload.local_checksum
    )
    download = None
    if needs_download and project.content_uri is not None:
        # Rate limit: max N signed download URL generations per project per window
        if not await rate_limit_check(
            settings.redis_url,
            str(user_id),
            str(project_id),
            settings.storage_rate_limit_max_requests,
            settings.storage_rate_limit_window_seconds,
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded: max {settings.storage_rate_limit_max_requests} "
                    f"signed URL requests per {settings.storage_rate_limit_window_seconds}s per project."
                ),
            )
        try:
            download = create_signed_project_download(
                settings,
                storage_uri=project.content_uri,
            )
        except ValueError as exc:
            raise _translate_blob_storage_error(exc)

    return ProjectSyncResponse(
        project=ProjectResponse.model_validate(project),
        needs_download=needs_download,
        download=download,
    )


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    billing_manager: BillingManager = Depends(get_billing_manager),
) -> ProjectResponse:
    user_id = _current_user_id(current_user)
    await _enforce_project_creation_rate_limit(user_id)
    await _enforce_project_creation_limit(
        user_id=user_id,
        user_repo=user_repo,
        billing_manager=billing_manager,
    )
    project = await project_repo.create(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        metadata_json=payload.metadata_json,
    )
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> None:
    user_id = _current_user_id(current_user)
    project = await project_repo.get(project_id=project_id, user_id=user_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    try:
        await run_in_threadpool(
            delete_project_prefix,
            settings,
            user_id=user_id,
            project_id=project_id,
        )
    except ValueError as exc:
        raise _translate_blob_storage_error(exc)

    deleted = await project_repo.delete(project_id=project_id, user_id=user_id)
    if not deleted:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
