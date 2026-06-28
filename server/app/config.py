"""
Config: non-secret settings from config/{env}.ini, secrets from env vars.
LOGSIGHT_ENV selects which ini file to load (default: dev).
"""
import configparser
import json
import os
from pathlib import Path

from pydantic_settings import BaseSettings


def _load_ini() -> configparser.ConfigParser:
    env = os.environ.get("LOGSIGHT_ENV", "dev")
    ini_path = Path(__file__).parent.parent / "config" / f"{env}.ini"
    if not ini_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {ini_path} (LOGSIGHT_ENV={env!r})"
        )
    cfg = configparser.ConfigParser()
    cfg.read(ini_path)
    return cfg


_ini = _load_ini()


class _Secrets(BaseSettings):
    db_password: str = "logsight"
    anthropic_api_key: str = ""

    model_config = {"env_prefix": "LOGSIGHT_", "env_file": ".env", "extra": "ignore"}


_secrets = _Secrets()


def get_db_url() -> str:
    """Assemble async DB URL from ini (host/port/name/user) + secret password."""
    db = _ini["database"]
    return (
        f"postgresql+asyncpg://{db['user']}:{_secrets.db_password}"
        f"@{db['host']}:{db['port']}/{db['name']}"
    )


def get_sync_db_url() -> str:
    """Synchronous DB URL for Alembic migrations."""
    db = _ini["database"]
    return (
        f"postgresql+psycopg2://{db['user']}:{_secrets.db_password}"
        f"@{db['host']}:{db['port']}/{db['name']}"
    )


class Settings:
    database_url: str = get_db_url()
    anthropic_api_key: str = _secrets.anthropic_api_key
    host: str = _ini.get("server", "host", fallback="0.0.0.0")
    port: int = _ini.getint("server", "port", fallback=8080)
    cors_origins: list[str] = json.loads(
        _ini.get("server", "cors_origins", fallback='["*"]')
    )
    model: str = _ini.get("agent", "model", fallback="claude-sonnet-4-6")
    heartbeat_timeout: int = _ini.getint("agent", "heartbeat_timeout", fallback=90)


settings = Settings()
