"""Add default note

Revision ID: 3f1c9a7b2d10
Revises: 645089e5533c
Create Date: 2025-11-20 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f1c9a7b2d10"
down_revision: Union[str, Sequence[str], None] = "645089e5533c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "note",
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Existing owners get one of their notes as the default one
    op.execute(
        """
        UPDATE note SET is_default = true
        WHERE note_id IN (
            SELECT DISTINCT ON (owner) note_id
            FROM note
            ORDER BY owner, note_id
        )
        """
    )
    op.create_index(
        "uq_note_one_default_per_owner",
        "note",
        ["owner"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_note_one_default_per_owner", table_name="note")
    op.drop_column("note", "is_default")
