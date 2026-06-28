"""Tests for Alembic migrations against a SQLite test DB."""
import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine, inspect, text


@pytest.fixture
def sqlite_db(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test_migrations.db"
    os.environ["LOGSIGHT_TEST_DB_URL"] = db_url
    yield db_url
    os.environ.pop("LOGSIGHT_TEST_DB_URL", None)


def run_alembic(command: str, db_url: str) -> None:
    from alembic.config import Config
    from alembic import command as alembic_cmd

    ini_path = Path(__file__).parent.parent / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url)

    if command == "upgrade":
        alembic_cmd.upgrade(cfg, "head")
    elif command.startswith("downgrade"):
        rev = command.split(":", 1)[-1] if ":" in command else "-1"
        alembic_cmd.downgrade(cfg, rev)


def test_upgrade_creates_all_tables(sqlite_db):
    run_alembic("upgrade", sqlite_db)
    engine = create_engine(sqlite_db)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "namespaces" in tables
    assert "machines" in tables
    assert "sidecar_instances" in tables
    assert "process_definitions" in tables
    assert "machine_processes" in tables
    assert "conversations" in tables
    assert "messages" in tables
    engine.dispose()


def test_downgrade_reverts_conversations(sqlite_db):
    run_alembic("upgrade", sqlite_db)
    run_alembic("downgrade:-1", sqlite_db)  # rolls back 002_conversations

    engine = create_engine(sqlite_db)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "conversations" not in tables
    assert "messages" not in tables
    # Phase 1 tables remain
    assert "namespaces" in tables
    engine.dispose()


def test_full_downgrade(sqlite_db):
    run_alembic("upgrade", sqlite_db)
    run_alembic("downgrade:base", sqlite_db)

    engine = create_engine(sqlite_db)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    # Only the alembic_version table should remain
    assert "namespaces" not in tables
    assert "conversations" not in tables
    engine.dispose()


def test_upgrade_is_idempotent(sqlite_db):
    """Running upgrade twice should not fail."""
    run_alembic("upgrade", sqlite_db)
    run_alembic("upgrade", sqlite_db)
    engine = create_engine(sqlite_db)
    inspector = inspect(engine)
    assert "namespaces" in inspector.get_table_names()
    engine.dispose()
