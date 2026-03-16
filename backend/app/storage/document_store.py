from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.document import (
    Document,
    DocumentCreateRequest,
    DocumentUpdateRequest,
)
from app.storage.json_store import JsonStore


class DocumentStore(JsonStore):
    def create(self, *, user_id: str, payload: DocumentCreateRequest) -> Document:
        document = Document(
            id=uuid4().hex,
            user_id=user_id,
            title=payload.title,
            content=payload.content,
            updated_at=datetime.now(tz=timezone.utc).isoformat(),
            drive_file_id=payload.drive_file_id,
        )
        data = self._read()
        data[document.id] = document.model_dump(mode="json")
        self._write(data)
        return document

    def list_for_user(self, *, user_id: str) -> list[Document]:
        data = self._read()
        return [Document(**item) for item in data.values() if item.get("user_id") == user_id]

    def get(self, *, user_id: str, document_id: str) -> Document | None:
        data = self._read()
        payload = data.get(document_id)
        if not payload or payload.get("user_id") != user_id:
            return None
        return Document(**payload)

    def update(
        self,
        *,
        user_id: str,
        document_id: str,
        payload: DocumentUpdateRequest,
    ) -> Document | None:
        existing = self.get(user_id=user_id, document_id=document_id)
        if not existing:
            return None
        updated = existing.model_copy(
            update={
                "title": payload.title if payload.title is not None else existing.title,
                "content": payload.content if payload.content is not None else existing.content,
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        data = self._read()
        data[document_id] = updated.model_dump(mode="json")
        self._write(data)
        return updated

    def update_drive_metadata(
        self,
        *,
        user_id: str,
        document_id: str,
        file_id: str,
        file_url: str | None,
    ) -> Document | None:
        existing = self.get(user_id=user_id, document_id=document_id)
        if not existing:
            return None
        updated = existing.model_copy(
            update={
                "drive_file_id": file_id,
                "drive_file_url": file_url,
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        data = self._read()
        data[document_id] = updated.model_dump(mode="json")
        self._write(data)
        return updated
