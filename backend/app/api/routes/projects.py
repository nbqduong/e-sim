from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_project_repo
from app.repositories.project_repo import ProjectRepository
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.session_manager import SessionData

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> ProjectListResponse:
    projects = await project_repo.list_for_user(uuid.UUID(current_user.user_id))
    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects]
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> ProjectResponse:
    project = await project_repo.get(
        project_id=project_id, user_id=uuid.UUID(current_user.user_id)
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> ProjectResponse:
    project = await project_repo.create(
        user_id=uuid.UUID(current_user.user_id),
        title=payload.title,
        description=payload.description,
        content=payload.content,
        metadata_json=payload.metadata_json,
    )
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> ProjectResponse:
    update_data = payload.model_dump(exclude_unset=True)
    project = await project_repo.update(
        project_id=project_id,
        user_id=uuid.UUID(current_user.user_id),
        **update_data,
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    current_user: SessionData = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> None:
    deleted = await project_repo.delete(
        project_id=project_id, user_id=uuid.UUID(current_user.user_id)
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
