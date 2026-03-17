from __future__ import annotations

import uuid
from datetime import datetime
import asyncio

from app.celery_app import celery
from app.core.config import settings
from app.core.database import async_session_factory
from app.repositories.task_repo import TaskRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.user_repo import UserRepository
from app.services.google_drive import GoogleDriveService, DriveExportError, DriveAuthorizationError


@celery.task(bind=True)
def export_document_task(self, task_id: str, user_id: str, document_id: str, title: str, content: str, drive_file_id: str | None = None):
    """Celery task wrapper that runs the async export workflow in an asyncio event loop."""
    if async_session_factory is None:
        raise RuntimeError("Database is not configured. Set DATABASE_URL.")

    async def _run():
        async with async_session_factory() as session:
            task_repo = TaskRepository(session)
            doc_repo = DocumentRepository(session)
            user_repo = UserRepository(session)
            drive_service = GoogleDriveService(settings=settings, user_repo=user_repo)

            task_uuid = uuid.UUID(task_id)
            doc_uuid = uuid.UUID(document_id)

            await task_repo.update_status(task_id=task_uuid, status="RUNNING", started_at=datetime.utcnow())
            await session.commit()

            try:
                result = await drive_service.export_document(
                    user_id=user_id, title=title, content=content, drive_file_id=drive_file_id
                )
            except DriveAuthorizationError as exc:
                await task_repo.update_status(task_id=task_uuid, status="FAILED", error=str(exc), finished_at=datetime.utcnow())
                await session.commit()
                return {"status": "failed", "error": str(exc)}
            except DriveExportError as exc:
                await task_repo.update_status(task_id=task_uuid, status="FAILED", error=str(exc), finished_at=datetime.utcnow())
                await session.commit()
                return {"status": "failed", "error": str(exc)}

            try:
                await doc_repo.update_drive_metadata(
                    document_id=doc_uuid,
                    user_id=uuid.UUID(user_id),
                    drive_file_id=result["id"],
                    drive_file_url=result.get("webViewLink"),
                )
                await task_repo.update_status(task_id=task_uuid, status="SUCCESS", result_url=result.get("webViewLink"), finished_at=datetime.utcnow())
                await session.commit()
                return {"status": "success", "result": result}
            except Exception as exc:
                await task_repo.update_status(task_id=task_uuid, status="FAILED", error=str(exc), finished_at=datetime.utcnow())
                await session.commit()
                return {"status": "failed", "error": str(exc)}

    return asyncio.run(_run())
