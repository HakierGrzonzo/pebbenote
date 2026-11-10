"""Drop note.updated_at, it is the created_at of the latest revision

Revision ID: f7b1d2e3a4c5
Revises: e6a9c3d4f5b2
Create Date: 2026-11-10 19:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7b1d2e3a4c5"
down_revision: Union[str, Sequence[str], None] = "e6a9c3d4f5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("note", "updated_at")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "note",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE note SET updated_at = latest.created_at
        FROM (
            SELECT note_id, MAX(created_at) AS created_at
            FROM note_revision
            GROUP BY note_id
        ) AS latest
        WHERE note.note_id = latest.note_id
        """
    )
