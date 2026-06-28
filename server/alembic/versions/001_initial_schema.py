"""Initial schema: namespaces, machines, sidecar_instances, process_definitions, machine_processes

Revision ID: 001
Revises:
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "namespaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("created_at", sa.TIMESTAMP, server_default=sa.func.now()),
    )

    op.create_table(
        "machines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("namespace_id", sa.String(36), sa.ForeignKey("namespaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hostname", sa.String, nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("created_at", sa.TIMESTAMP, server_default=sa.func.now()),
    )

    op.create_table(
        "sidecar_instances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("machine_id", sa.String(36), sa.ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("port", sa.Integer, server_default="9000"),
        sa.Column("status", sa.String, server_default="alive"),
        sa.Column("last_heartbeat", sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column("registered_at", sa.TIMESTAMP, server_default=sa.func.now()),
    )

    op.create_table(
        "process_definitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("example_qa", sa.Text, server_default="[]"),
        sa.Column("created_at", sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP, server_default=sa.func.now()),
    )

    op.create_table(
        "machine_processes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("machine_id", sa.String(36), sa.ForeignKey("machines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("process_definition_id", sa.String(36), sa.ForeignKey("process_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("log_paths", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("machine_processes")
    op.drop_table("process_definitions")
    op.drop_table("sidecar_instances")
    op.drop_table("machines")
    op.drop_table("namespaces")
