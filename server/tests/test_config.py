"""Tests for config.py: ini loading and DB URL assembly."""
import os
import pytest
from unittest.mock import patch


def test_get_db_url_assembles_from_ini_and_env(tmp_path):
    ini = tmp_path / "dev.ini"
    ini.write_text(
        "[database]\nhost=localhost\nport=5432\nname=logsight\nuser=logsight\n"
        "[server]\nhost=0.0.0.0\nport=8080\ncors_origins=[\"*\"]\n"
        "[agent]\nmodel=claude-sonnet-4-6\nheartbeat_timeout=90\n"
    )
    with (
        patch.dict(os.environ, {"LOGSIGHT_ENV": "dev", "LOGSIGHT_DB_PASSWORD": "s3cr3t"}),
        patch("app.config.Path.__truediv__", return_value=ini),
    ):
        import importlib
        import app.config as cfg_mod
        importlib.reload(cfg_mod)
        url = cfg_mod.get_db_url()

    assert "s3cr3t" in url
    assert "localhost" in url
    assert "5432" in url
    assert "logsight" in url
    assert "postgresql+asyncpg" in url


def test_missing_env_raises_file_not_found(tmp_path):
    with patch.dict(os.environ, {"LOGSIGHT_ENV": "nonexistent_env_xyz"}):
        import importlib
        import app.config as cfg_mod
        with pytest.raises(FileNotFoundError, match="LOGSIGHT_ENV='nonexistent_env_xyz'"):
            importlib.reload(cfg_mod)


def test_db_password_never_in_ini(tmp_path):
    """The ini file should not contain the DB password."""
    import app.config as cfg_mod
    # Read whatever ini file is currently in use
    ini_path = next(
        (p for p in [
            cfg_mod.Path(__file__).parent.parent / "config" / f"{os.environ.get('LOGSIGHT_ENV', 'dev')}.ini"
        ] if p.exists()),
        None,
    )
    if ini_path:
        content = ini_path.read_text()
        assert "password" not in content.lower()
        assert "sk-ant-" not in content
