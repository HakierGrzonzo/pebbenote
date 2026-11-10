"""Keep the standing instructions as revisions of a list per user

Revision ID: e6a9c3d4f5b2
Revises: d5f8b2c3e4a1
Create Date: 2026-11-10 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6a9c3d4f5b2"
down_revision: Union[str, Sequence[str], None] = "d5f8b2c3e4a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "instruction_list",
        sa.Column(
            "instruction_list_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("instruction_list_id"),
        sa.UniqueConstraint("owner"),
    )
    op.create_table(
        "instruction_revision",
        sa.Column(
            "instruction_revision_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("instruction_list_id", sa.Uuid(), nullable=False),
        sa.Column("instructions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instruction_list_id"], ["instruction_list.instruction_list_id"]
        ),
        sa.PrimaryKeyConstraint("instruction_revision_id"),
    )
    op.create_index(
        "ix_instruction_revision_list_created",
        "instruction_revision",
        ["instruction_list_id", "created_at"],
    )
    op.execute(
        """
        INSERT INTO instruction_list (owner)
        SELECT DISTINCT owner FROM user_instruction
        """
    )
    op.execute(
        """
        INSERT INTO instruction_revision (instruction_list_id, instructions)
        SELECT
            instruction_list.instruction_list_id,
            array_agg(
                user_instruction.instruction_text ORDER BY user_instruction.created_at
            )
        FROM instruction_list
        JOIN user_instruction USING (owner)
        GROUP BY instruction_list.instruction_list_id
        """
    )
    op.drop_index(op.f("ix_user_instruction_owner"), table_name="user_instruction")
    op.drop_table("user_instruction")


def downgrade() -> None:
    """Downgrade schema."""
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
    # Only the latest revision of each list survives, in its order
    op.execute(
        """
        WITH latest_revision_id AS (
            SELECT DISTINCT ON (instruction_list_id)
                instruction_list_id, instruction_revision_id
            FROM instruction_revision
            ORDER BY instruction_list_id, created_at DESC
        )
        INSERT INTO user_instruction (owner, instruction_text, created_at)
        SELECT
            instruction_list.owner,
            instruction.instruction_text,
            instruction_revision.created_at
                + instruction.position * interval '1 microsecond'
        FROM latest_revision_id
        JOIN instruction_list USING (instruction_list_id)
        JOIN instruction_revision USING (instruction_revision_id)
        CROSS JOIN LATERAL unnest(instruction_revision.instructions)
            WITH ORDINALITY AS instruction (instruction_text, position)
        """
    )
    op.drop_index(
        "ix_instruction_revision_list_created", table_name="instruction_revision"
    )
    op.drop_table("instruction_revision")
    op.drop_table("instruction_list")
