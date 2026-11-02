"""Add action status and updated_at

Revision ID: c4e7a1d9b302
Revises: 8b2d4e6f1a35
Create Date: 2026-11-01 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e7a1d9b302"
down_revision: Union[str, Sequence[str], None] = "8b2d4e6f1a35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

action_status = postgresql.ENUM("pending", "done", "failed", name="action_status")


def upgrade() -> None:
    """Upgrade schema."""
    action_status.create(op.get_bind())
    op.add_column(
        "note_action",
        sa.Column("status", action_status, server_default="done", nullable=False),
    )
    for table in ("note", "note_action"):
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("clock_timestamp()"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("note_action", "updated_at")
    op.drop_column("note", "updated_at")
    op.drop_column("note_action", "status")
    action_status.drop(op.get_bind())
