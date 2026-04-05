from __future__ import annotations

import uuid

import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_current_user,
    get_document_repo,
    get_project_repo,
    get_task_repo,
)
from app.core.config import settings
from app.core.database import async_session_factory
from app.repositories.document_repo import DocumentRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.task_repo import TaskRepository
from app.repositories.user_repo import UserRepository
from app.schemas.document import (
    DocumentCreateRequest,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    DriveSaveResponse,
)
from app.services.google_drive import DriveAuthorizationError, DriveExportError, GoogleDriveService
from app.services.session_manager import SessionData

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/project/{project_id}", response_model=DocumentListResponse)
async def list_documents(
    project_id: uuid.UUID,
    current_user: SessionData = Depends(get_current_user),
    doc_repo: DocumentRepository = Depends(get_document_repo),
) -> DocumentListResponse:
    docs = await doc_repo.list_for_project(
        project_id=project_id, user_id=uuid.UUID(current_user.user_id)
    )
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs]
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: SessionData = Depends(get_current_user),
    doc_repo: DocumentRepository = Depends(get_document_repo),
) -> DocumentResponse:
    doc = await doc_repo.get(document_id=document_id, user_id=uuid.UUID(current_user.user_id))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreateRequest,
    current_user: SessionData = Depends(get_current_user),
    doc_repo: DocumentRepository = Depends(get_document_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> DocumentResponse:
    project = await project_repo.get(
        user_id=uuid.UUID(current_user.user_id),
        project_id=payload.project_id,
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    doc = await doc_repo.create(
        project_id=payload.project_id,
        user_id=uuid.UUID(current_user.user_id),
        title=payload.title,
        content=payload.content,
    )
    return DocumentResponse.model_validate(doc)


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdateRequest,
    current_user: SessionData = Depends(get_current_user),
    doc_repo: DocumentRepository = Depends(get_document_repo),
) -> DocumentResponse:
    update_data = payload.model_dump(exclude_unset=True)
    doc = await doc_repo.update(
        document_id=document_id,
        user_id=uuid.UUID(current_user.user_id),
        **update_data,
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: SessionData = Depends(get_current_user),
    doc_repo: DocumentRepository = Depends(get_document_repo),
) -> None:
    deleted = await doc_repo.delete(
        document_id=document_id, user_id=uuid.UUID(current_user.user_id)
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


@router.post("/{document_id}/drive", response_model=DriveSaveResponse)
async def save_document_to_drive(
    document_id: uuid.UUID,
    current_user: SessionData = Depends(get_current_user),
    doc_repo: DocumentRepository = Depends(get_document_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
) -> DriveSaveResponse:
    doc = await doc_repo.get(
        document_id=document_id, user_id=uuid.UUID(current_user.user_id)
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Create a persistent task row so clients can query status later.
    task = await task_repo.create(
        user_id=uuid.UUID(current_user.user_id),
        task_type="drive_export",
        document_id=document_id,
    )

    # Enqueue Celery task to perform the export in a worker process.
    try:
        from app.tasks.drive_tasks import export_document_task

        export_document_task.delay(
            str(task.id),
            current_user.user_id,
            str(document_id),
            doc.title,
            doc.content,
            doc.drive_file_id,
        )
    except Exception:
        logging.exception("Failed to enqueue Celery export task; falling back to background thread")

        async def _export_and_update(task_id: uuid.UUID):
            from datetime import datetime

            if async_session_factory is None:
                logging.error("Database is not configured; cannot run drive export fallback")
                return

            async with async_session_factory() as session:
                task_repo_bg = TaskRepository(session)
                doc_repo_bg = DocumentRepository(session)
                user_repo_bg = UserRepository(session)
                drive_service_bg = GoogleDriveService(settings=settings, user_repo=user_repo_bg)

                try:
                    await task_repo_bg.update_status(task_id=task_id, status="RUNNING", started_at=datetime.utcnow())
                    await session.commit()
                    result = await drive_service_bg.export_document(
                        user_id=current_user.user_id,
                        title=doc.title,
                        content=doc.content,
                        drive_file_id=doc.drive_file_id,
                    )
                except DriveAuthorizationError as exc:
                    logging.exception("Drive authorization failed during background export: %s", exc)
                    await task_repo_bg.update_status(task_id=task_id, status="FAILED", error=str(exc), finished_at=datetime.utcnow())
                    await session.commit()
                    return
                except DriveExportError as exc:
                    logging.exception("Drive export failed during background export: %s", exc)
                    await task_repo_bg.update_status(task_id=task_id, status="FAILED", error=str(exc), finished_at=datetime.utcnow())
                    await session.commit()
                    return

                try:
                    await doc_repo_bg.update_drive_metadata(
                        document_id=document_id,
                        user_id=uuid.UUID(current_user.user_id),
                        drive_file_id=result["id"],
                        drive_file_url=result.get("webViewLink"),
                    )
                    await task_repo_bg.update_status(task_id=task_id, status="SUCCESS", result_url=result.get("webViewLink"), finished_at=datetime.utcnow())
                    await session.commit()
                except Exception as exc:
                    logging.exception("Failed to persist drive metadata after export")
                    await task_repo_bg.update_status(task_id=task_id, status="FAILED", error=str(exc), finished_at=datetime.utcnow())
                    await session.commit()

        asyncio.create_task(_export_and_update(task.id))

    # Return current metadata immediately. If no drive file exists yet, return empty id and None URL.
    return DriveSaveResponse(
        drive_file_id=doc.drive_file_id or "",
        drive_file_url=doc.drive_file_url,
    )
