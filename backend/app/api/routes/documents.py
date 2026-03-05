from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_current_user,
    get_document_store,
    get_google_drive_service,
)
from app.schemas.document import (
    Document,
    DocumentCreateRequest,
    DocumentListResponse,
    DocumentUpdateRequest,
    DriveSaveResponse,
)
from app.services.google_drive import DriveAuthorizationError, DriveExportError, GoogleDriveService
from app.services.session_manager import SessionData
from app.storage.document_store import DocumentStore

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: SessionData = Depends(get_current_user),
    drive_service: GoogleDriveService = Depends(get_google_drive_service),
) -> DocumentListResponse:
    try:
        drive_files = drive_service.list_documents(user_id=current_user.user_id)
    except DriveAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except DriveExportError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    documents = []
    for f in drive_files:
        documents.append(
            Document(
                id=f["id"],
                user_id=current_user.user_id,
                title=f["name"].replace(".txt", ""),
                content="",  # Content is not fetched during listing
                updated_at=f.get("modifiedTime", ""),
                drive_file_id=f["id"],
                drive_file_url=f.get("webViewLink"),
            )
        )

    return DocumentListResponse(documents=documents)


@router.post("/", response_model=Document, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreateRequest,
    current_user: SessionData = Depends(get_current_user),
    store: DocumentStore = Depends(get_document_store),
) -> Document:
    return store.create(user_id=current_user.user_id, payload=payload)


@router.put("/{document_id}", response_model=Document)
async def update_document(
    document_id: str,
    payload: DocumentUpdateRequest,
    current_user: SessionData = Depends(get_current_user),
    store: DocumentStore = Depends(get_document_store),
) -> Document:
    document = store.update(user_id=current_user.user_id, document_id=document_id, payload=payload)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("/{document_id}/drive", response_model=DriveSaveResponse)
async def save_document_to_drive(
    document_id: str,
    current_user: SessionData = Depends(get_current_user),
    store: DocumentStore = Depends(get_document_store),
    drive_service: GoogleDriveService = Depends(get_google_drive_service),
) -> DriveSaveResponse:
    document = store.get(user_id=current_user.user_id, document_id=document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        result = drive_service.export_document(user_id=current_user.user_id, document=document)
    except DriveAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except DriveExportError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    updated = store.update_drive_metadata(
        user_id=current_user.user_id,
        document_id=document_id,
        file_id=result["id"],
        file_url=result.get("webViewLink"),
    )
    if updated is None:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return DriveSaveResponse(
        drive_file_id=result["id"],
        drive_file_url=result.get("webViewLink"),
    )
