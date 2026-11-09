"""Add note revisions, the note content moves to its latest revision

Revision ID: d5f8b2c3e4a1
Revises: c4e7a1d9b302
Create Date: 2026-11-09 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5f8b2c3e4a1"
down_revision: Union[str, Sequence[str], None] = "c4e7a1d9b302"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Old actions have no snapshots to pair with, so history starts fresh
    op.execute("DELETE FROM note_action")
    op.create_table(
        "note_revision",
        sa.Column(
            "note_revision_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("note_id", sa.Uuid(), nullable=False),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column("note_action_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["note_id"], ["note.note_id"]),
        sa.ForeignKeyConstraint(["note_action_id"], ["note_action.note_action_id"]),
        sa.PrimaryKeyConstraint("note_revision_id"),
        sa.UniqueConstraint("note_action_id"),
    )
    op.create_index(
        "ix_note_revision_note_created",
        "note_revision",
        ["note_id", "created_at"],
    )
    op.execute(
        """
        INSERT INTO note_revision (note_id, note_text, created_at)
        SELECT note_id, note_text, updated_at FROM note
        """
    )
    op.drop_column("note", "note_text")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("note", sa.Column("note_text", sa.Text(), nullable=True))
    op.execute(
        """
        WITH latest_revision_id AS (
            SELECT DISTINCT ON (note_id) note_id, note_revision_id
            FROM note_revision
            ORDER BY note_id, created_at DESC
        )
        UPDATE note SET note_text = note_revision.note_text
        FROM latest_revision_id
        JOIN note_revision USING (note_revision_id)
        WHERE note.note_id = latest_revision_id.note_id
        """
    )
    op.execute("UPDATE note SET note_text = '' WHERE note_text IS NULL")
    op.alter_column("note", "note_text", nullable=False)
    op.drop_index("ix_note_revision_note_created", table_name="note_revision")
    op.drop_table("note_revision")
