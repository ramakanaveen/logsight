"""Convert TEXT columns to native JSONB/ARRAY types on PostgreSQL

Revision ID: 004
Revises: 003
Create Date: 2026-06-28

ORM uses JsonBlob (→ JSONB) and StringArray (→ TEXT[]) on PostgreSQL but the
initial migration created them as plain TEXT. asyncpg cannot bind a Python
list/dict to a TEXT column, causing 500 errors on inserts.
"""
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_context().bind
    if bind is None or bind.dialect.name != "postgresql":
        return

    # process_definitions.example_qa: TEXT → JSONB
    # Must drop the server default first; PostgreSQL can't auto-cast TEXT default '[]' to JSONB
    op.execute("ALTER TABLE process_definitions ALTER COLUMN example_qa DROP DEFAULT")
    op.execute(
        "ALTER TABLE process_definitions "
        "ALTER COLUMN example_qa TYPE JSONB USING example_qa::JSONB"
    )
    op.execute("ALTER TABLE process_definitions ALTER COLUMN example_qa SET DEFAULT '[]'::JSONB")

    # machine_processes.log_paths: TEXT → TEXT[]
    # USING clause can't contain subqueries, so use a temp-column swap via DO block
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE machine_processes ADD COLUMN log_paths_new TEXT[];
            UPDATE machine_processes
               SET log_paths_new = ARRAY(
                       SELECT jsonb_array_elements_text(log_paths::JSONB)
                   );
            ALTER TABLE machine_processes DROP COLUMN log_paths;
            ALTER TABLE machine_processes RENAME COLUMN log_paths_new TO log_paths;
            ALTER TABLE machine_processes ALTER COLUMN log_paths SET NOT NULL;
        END $$;
    """)

    # messages.metadata: TEXT → JSONB
    op.execute("ALTER TABLE messages ALTER COLUMN metadata DROP DEFAULT")
    op.execute(
        "ALTER TABLE messages "
        "ALTER COLUMN metadata TYPE JSONB USING metadata::JSONB"
    )
    op.execute("ALTER TABLE messages ALTER COLUMN metadata SET DEFAULT '{}'::JSONB")


def downgrade() -> None:
    bind = op.get_context().bind
    if bind is None or bind.dialect.name != "postgresql":
        return

    op.execute(
        "ALTER TABLE messages "
        "ALTER COLUMN metadata TYPE TEXT USING metadata::TEXT"
    )
    op.execute(
        "ALTER TABLE machine_processes "
        "ALTER COLUMN log_paths TYPE TEXT USING array_to_json(log_paths)::TEXT"
    )
    op.execute(
        "ALTER TABLE process_definitions "
        "ALTER COLUMN example_qa TYPE TEXT USING example_qa::TEXT"
    )
