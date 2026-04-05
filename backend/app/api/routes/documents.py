from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_current_user,
    get_document_repo,
    get_project_repo,
)
from app.repositories.document_repo import DocumentRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.document import (
    DocumentCreateRequest,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
)
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
