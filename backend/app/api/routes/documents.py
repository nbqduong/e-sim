from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_current_user,
    get_document_repo,
    get_google_drive_service,
)
from app.repositories.document_repo import DocumentRepository
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
) -> DocumentResponse:
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
    drive_service: GoogleDriveService = Depends(get_google_drive_service),
) -> DriveSaveResponse:
    doc = await doc_repo.get(
        document_id=document_id, user_id=uuid.UUID(current_user.user_id)
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        result = await drive_service.export_document(
            user_id=current_user.user_id, title=doc.title, content=doc.content,
            drive_file_id=doc.drive_file_id,
        )
    except DriveAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except DriveExportError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    await doc_repo.update_drive_metadata(
        document_id=document_id,
        user_id=uuid.UUID(current_user.user_id),
        drive_file_id=result["id"],
        drive_file_url=result.get("webViewLink"),
    )

    return DriveSaveResponse(
        drive_file_id=result["id"],
        drive_file_url=result.get("webViewLink"),
    )
