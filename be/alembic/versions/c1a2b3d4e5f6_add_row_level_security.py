"""Row level security: an app role that only sees the rows of its user

The app connects as POSTGRES_APP_USER and sets pebbenote.user per
transaction. Without that setting the policies show no rows.

Revision ID: c1a2b3d4e5f6
Revises: b9d3e5f7a2c6
Create Date: 2026-11-24 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from pebbenote.config import settings

# revision identifiers, used by Alembic.
revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b9d3e5f7a2c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CURRENT_USER = "current_setting('pebbenote.user', true)"

# Table, the condition a row of it is visible under
POLICIES = {
    "note": f"owner = {CURRENT_USER}",
    "instruction_list": f"owner = {CURRENT_USER}",
    # The subqueries are filtered by the policies of the parent table
    "note_action": (
        "EXISTS (SELECT 1 FROM note WHERE note.note_id = note_action.note_id)"
    ),
    "note_revision": (
        "EXISTS (SELECT 1 FROM note WHERE note.note_id = note_revision.note_id)"
    ),
    "instruction_revision": (
        "EXISTS (SELECT 1 FROM instruction_list WHERE "
        "instruction_list.instruction_list_id = "
        "instruction_revision.instruction_list_id)"
    ),
}

OWNED_TABLES = ["note", "instruction_list"]


def upgrade() -> None:
    """Upgrade schema."""
    role = settings.POSTGRES_APP_USER
    # Roles belong to the cluster, the test database shares it with the app's
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{role}') THEN
                    CREATE ROLE "{role}" LOGIN NOSUPERUSER NOBYPASSRLS;
                END IF;
            END
            $$
            """
        )
    )
    # ALTER ROLE takes no bind parameters, format() quotes the password
    alter_role = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT format('ALTER ROLE %I PASSWORD %L', "
                "CAST(:role AS text), CAST(:password AS text))"
            ),
            {"role": role, "password": settings.POSTGRES_APP_PASSWORD},
        )
        .scalar_one()
    )
    op.execute(sa.text(alter_role))

    op.execute(f'GRANT USAGE ON SCHEMA public TO "{role}"')
    for table, condition in POLICIES.items():
        op.execute(f'GRANT SELECT, INSERT, UPDATE ON {table} TO "{role}"')
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY owner_only ON {table} "
            f"USING ({condition}) WITH CHECK ({condition})"
        )

    # Without the setting an insert fails instead of making an ownerless row
    for table in OWNED_TABLES:
        op.alter_column(
            table, "owner", server_default=sa.text("current_setting('pebbenote.user')")
        )


def downgrade() -> None:
    """Downgrade schema."""
    role = settings.POSTGRES_APP_USER
    for table in OWNED_TABLES:
        op.alter_column(table, "owner", server_default=None)

    for table in POLICIES:
        op.execute(f"DROP POLICY owner_only ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f'REVOKE ALL ON {table} FROM "{role}"')
    op.execute(f'REVOKE USAGE ON SCHEMA public FROM "{role}"')
    # The role stays, other databases of the cluster may still use it
