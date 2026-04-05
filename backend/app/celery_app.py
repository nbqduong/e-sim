from __future__ import annotations

from celery import Celery
from app.core.config import settings

celery = Celery(
    "e_sim",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
