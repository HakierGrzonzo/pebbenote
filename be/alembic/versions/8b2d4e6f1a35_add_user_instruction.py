"""Add user instruction table

Revision ID: 8b2d4e6f1a35
Revises: 3f1c9a7b2d10
Create Date: 2026-10-24 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b2d4e6f1a35"
down_revision: Union[str, Sequence[str], None] = "3f1c9a7b2d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_instruction",
        sa.Column(
            "instruction_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("instruction_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("instruction_id"),
    )
    op.create_index(
        op.f("ix_user_instruction_owner"), "user_instruction", ["owner"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_instruction_owner"), table_name="user_instruction")
    op.drop_table("user_instruction")
