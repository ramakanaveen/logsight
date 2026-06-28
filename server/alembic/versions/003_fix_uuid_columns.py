"""Convert VARCHAR(36) UUID columns to native PostgreSQL UUID type

Revision ID: 003
Revises: 002
Create Date: 2026-06-28

SQLAlchemy ORM models use UUID(as_uuid=True) which causes PostgreSQL to bind
parameters as ::UUID. The initial migrations used String(36) for SQLite
compatibility, leaving VARCHAR(36) columns in Postgres that reject uuid params.
This migration casts all id/fk columns to native UUID on PostgreSQL; it is a
no-op on SQLite.
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_context().bind
    if bind is None or bind.dialect.name != "postgresql":
        return

    # Drop all FK constraints on affected tables so we can change column types
    op.execute("""
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN (
                SELECT conname, conrelid::regclass::text AS tbl
                FROM pg_constraint
                WHERE contype = 'f'
                  AND conrelid::regclass::text IN (
                      'machines', 'sidecar_instances',
                      'machine_processes', 'messages'
                  )
            ) LOOP
                EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.tbl, r.conname);
            END LOOP;
        END $$;
    """)

    # Convert every id/fk column from VARCHAR(36) → UUID
    for tbl, col in [
        ("namespaces",           "id"),
        ("machines",             "id"),
        ("machines",             "namespace_id"),
        ("sidecar_instances",    "id"),
        ("sidecar_instances",    "machine_id"),
        ("process_definitions",  "id"),
        ("machine_processes",    "id"),
        ("machine_processes",    "machine_id"),
        ("machine_processes",    "process_definition_id"),
        ("conversations",        "id"),
        ("messages",             "id"),
        ("messages",             "conversation_id"),
    ]:
        op.execute(
            f'ALTER TABLE {tbl} ALTER COLUMN "{col}" TYPE UUID USING "{col}"::UUID'
        )

    # Re-add FK constraints with explicit names
    op.execute(
        "ALTER TABLE machines ADD CONSTRAINT machines_namespace_id_fkey "
        "FOREIGN KEY (namespace_id) REFERENCES namespaces(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE sidecar_instances ADD CONSTRAINT sidecar_instances_machine_id_fkey "
        "FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE machine_processes ADD CONSTRAINT machine_processes_machine_id_fkey "
        "FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE machine_processes ADD CONSTRAINT machine_processes_process_definition_id_fkey "
        "FOREIGN KEY (process_definition_id) REFERENCES process_definitions(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE messages ADD CONSTRAINT messages_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE"
    )


def downgrade() -> None:
    bind = op.get_context().bind
    if bind is None or bind.dialect.name != "postgresql":
        return

    # Drop FK constraints before changing types back
    op.execute("""
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN (
                SELECT conname, conrelid::regclass::text AS tbl
                FROM pg_constraint
                WHERE contype = 'f'
                  AND conrelid::regclass::text IN (
                      'machines', 'sidecar_instances',
                      'machine_processes', 'messages'
                  )
            ) LOOP
                EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.tbl, r.conname);
            END LOOP;
        END $$;
    """)

    for tbl, col in [
        ("messages",             "conversation_id"),
        ("messages",             "id"),
        ("conversations",        "id"),
        ("machine_processes",    "process_definition_id"),
        ("machine_processes",    "machine_id"),
        ("machine_processes",    "id"),
        ("process_definitions",  "id"),
        ("sidecar_instances",    "machine_id"),
        ("sidecar_instances",    "id"),
        ("machines",             "namespace_id"),
        ("machines",             "id"),
        ("namespaces",           "id"),
    ]:
        op.execute(
            f'ALTER TABLE {tbl} ALTER COLUMN "{col}" TYPE VARCHAR(36) USING "{col}"::TEXT'
        )

    op.execute(
        "ALTER TABLE machines ADD CONSTRAINT machines_namespace_id_fkey "
        "FOREIGN KEY (namespace_id) REFERENCES namespaces(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE sidecar_instances ADD CONSTRAINT sidecar_instances_machine_id_fkey "
        "FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE machine_processes ADD CONSTRAINT machine_processes_machine_id_fkey "
        "FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE machine_processes ADD CONSTRAINT machine_processes_process_definition_id_fkey "
        "FOREIGN KEY (process_definition_id) REFERENCES process_definitions(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE messages ADD CONSTRAINT messages_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE"
    )
