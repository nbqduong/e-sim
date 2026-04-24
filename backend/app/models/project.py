from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=func.cast('{}', JSONB))
    content_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")
