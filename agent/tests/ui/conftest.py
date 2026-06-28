"""
UI test setup: LLM patching + live server + per-test cleanup.

The server is started at module import time (not in a session fixture) to
avoid pytest-asyncio interfering with session-scoped yield fixtures.
"""
import os
import socket
import tempfile
import threading
import time
from unittest.mock import MagicMock

import httpx
import pytest
import uvicorn
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ── LLM patch ────────────────────────────────────────────────────────────────
# Must happen before 'main' imports the route handlers.
import app.services.llm as llm_module


def _identify(question, processes):
    return {"relevant_process_ids": [p["id"] for p in processes], "keywords": ["test"]}


llm_module.identify_processes = MagicMock(side_effect=_identify)
llm_module.summarize_results = MagicMock(return_value="Test log summary from mock LLM.")

# ── DB + server setup (module-level, runs once per process) ──────────────────
from app.db.database import get_db
from app.db.models import Base
from main import app

_tmpdir = tempfile.mkdtemp(prefix="logsight_ui_test_")
_DB_PATH = os.path.join(_tmpdir, "ui_test.db")
_LIVE_SERVER_URL = "http://127.0.0.1:18080"

# Create schema synchronously — no asyncio loop needed.
_sync_engine = create_engine(f"sqlite:///{_DB_PATH}")
Base.metadata.create_all(_sync_engine)
_sync_engine.dispose()

# Async engine for the FastAPI app running in uvicorn's event loop.
_async_engine = create_async_engine(f"sqlite+aiosqlite:///{_DB_PATH}")
_AsyncSession = async_sessionmaker(_async_engine, expire_on_commit=False)


async def _override_get_db():
    async with _AsyncSession() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db

# Start uvicorn in a daemon thread.
_config = uvicorn.Config(app, host="127.0.0.1", port=18080, log_level="error", loop="asyncio")
_server = uvicorn.Server(_config)
_server_thread = threading.Thread(target=_server.run, daemon=True)
_server_thread.start()

# Wait until the port is open (max 5 s).
for _ in range(50):
    try:
        with socket.create_connection(("127.0.0.1", 18080), timeout=0.1):
            break
    except OSError:
        time.sleep(0.1)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def setup_db():
    """Override the parent conftest's async autouse setup_db so it doesn't run here."""


@pytest.fixture
def live_server():
    """Return the base URL of the running test server."""
    return _LIVE_SERVER_URL


@pytest.fixture(autouse=True)
def clean_processes():
    """Delete all processes before each UI test for isolation."""
    resp = httpx.get(f"{_LIVE_SERVER_URL}/v1/processes", timeout=5)
    for proc in resp.json():
        httpx.delete(f"{_LIVE_SERVER_URL}/v1/processes/{proc['id']}", timeout=5)
