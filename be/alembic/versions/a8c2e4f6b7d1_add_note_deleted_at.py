"""Add note.deleted_at, deleted notes are kept with their history

Revision ID: a8c2e4f6b7d1
Revises: f7b1d2e3a4c5
Create Date: 2026-11-23 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8c2e4f6b7d1"
down_revision: Union[str, Sequence[str], None] = "f7b1d2e3a4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "note", sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Deleted notes would come back, drop them with their history instead
    op.execute(
        """
        DELETE FROM note_revision
        WHERE note_id IN (SELECT note_id FROM note WHERE deleted_at IS NOT NULL)
        """
    )
    op.execute(
        """
        DELETE FROM note_action
        WHERE note_id IN (SELECT note_id FROM note WHERE deleted_at IS NOT NULL)
        """
    )
    op.execute("DELETE FROM note WHERE deleted_at IS NOT NULL")
    op.drop_column("note", "deleted_at")
