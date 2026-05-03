"""move project content to gcs

Revision ID: 7f4e6c5b9d12
Revises: c7d8e9f0a1b2
Create Date: 2026-04-23 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f4e6c5b9d12"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("content_uri", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("content_checksum", sa.String(length=128), nullable=True))
    op.add_column("projects", sa.Column("content_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("content_size_bytes", sa.Integer(), nullable=True))
    op.drop_column("projects", "content")


def downgrade() -> None:
    op.add_column("projects", sa.Column("content", sa.Text(), server_default="", nullable=False))
    op.drop_column("projects", "content_size_bytes")
    op.drop_column("projects", "content_updated_at")
    op.drop_column("projects", "content_checksum")
    op.drop_column("projects", "content_uri")
