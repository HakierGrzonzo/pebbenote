"""Add note.title, a name for the note made by the LLM

Revision ID: b9d3e5f7a2c6
Revises: a8c2e4f6b7d1
Create Date: 2026-11-24 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9d3e5f7a2c6"
down_revision: Union[str, Sequence[str], None] = "a8c2e4f6b7d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("note", sa.Column("title", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("note", "title")
