from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        content: str = "",
    ) -> Document:
        doc = Document(
            project_id=project_id,
            user_id=user_id,
            title=title,
            content=content,
        )
        self._session.add(doc)
        await self._session.flush()
        return doc

    async def list_for_project(
        self, *, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.project_id == project_id, Document.user_id == user_id)
            .order_by(Document.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get(
        self, *, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> Document | None:
        result = await self._session.execute(
            select(Document)
            .where(Document.id == document_id, Document.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        *,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str | None = None,
        content: str | None = None,
    ) -> Document | None:
        doc = await self.get(document_id=document_id, user_id=user_id)
        if doc is None:
            return None
        if title is not None:
            doc.title = title
        if content is not None:
            doc.content = content
        await self._session.flush()
        return doc

    async def update_drive_metadata(
        self,
        *,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        drive_file_id: str,
        drive_file_url: str | None = None,
    ) -> Document | None:
        doc = await self.get(document_id=document_id, user_id=user_id)
        if doc is None:
            return None
        doc.drive_file_id = drive_file_id
        doc.drive_file_url = drive_file_url
        await self._session.flush()
        return doc

    async def delete(self, *, document_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        doc = await self.get(document_id=document_id, user_id=user_id)
        if doc is None:
            return False
        await self._session.delete(doc)
        await self._session.flush()
        return True
