"""add user billing and project count

Revision ID: 8d4a1f7c2b31
Revises: 7f4e6c5b9d12
Create Date: 2026-04-25 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8d4a1f7c2b31"
down_revision: Union[str, None] = "7f4e6c5b9d12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("billing_tier", sa.String(length=32), server_default="free", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("project_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET project_count = project_totals.project_count
            FROM (
                SELECT user_id, COUNT(*)::integer AS project_count
                FROM projects
                GROUP BY user_id
            ) AS project_totals
            WHERE users.id = project_totals.user_id
            """
        )
    )


def downgrade() -> None:
    op.drop_column("users", "project_count")
    op.drop_column("users", "billing_tier")
