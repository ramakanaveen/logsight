import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock, AsyncMock, patch

from app.db.models import Base, Namespace, Machine, SidecarInstance, ProcessDefinition, MachineProcess
from app.db.database import get_db
from main import app


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Process definition fixtures ───────────────────────────────────────────────

@pytest.fixture
def sample_process_payload():
    return {
        "name": "CurveBuilder",
        "description": "Builds yield curves each morning",
        "example_qa": [{"question": "Is curve done?", "answer": "Look for completed"}],
    }


@pytest.fixture
async def created_process(client, sample_process_payload):
    resp = await client.post("/v1/processes", json=sample_process_payload)
    assert resp.status_code == 201
    return resp.json()


# ── Topology fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
async def namespace(client):
    resp = await client.post("/v1/namespaces", json={"name": "STIRT", "description": "Test NS"})
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def machine(client, namespace):
    ns_id = namespace["id"]
    resp = await client.post(
        f"/v1/namespaces/{ns_id}/machines",
        json={"hostname": "server1.stirt.internal", "description": "Test machine"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def sidecar(client, machine):
    resp = await client.post(
        "/v1/sidecars/register",
        json={"machine_host": "server1.stirt.internal", "port": 9000},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def machine_process(client, machine, created_process):
    machine_id = machine["id"]
    process_id = created_process["id"]
    resp = await client.post(
        f"/v1/machines/{machine_id}/processes",
        json={"process_definition_id": process_id, "log_paths": ["/opt/curve/logs/*.log"]},
    )
    assert resp.status_code == 201
    return resp.json()


# ── LLM / agent mock fixtures ─────────────────────────────────────────────────

@pytest.fixture
def mock_agent():
    """Mock the entire run_agent coroutine to return a canned answer."""
    async def _fake_run_agent(*, question, process_hint, history, process_definitions, db, emit):
        await emit("thinking", {"text": "Thinking..."})
        await emit("answer", {"text": "Curve building completed at 14:23 on server1."})
        await emit("usage", {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150, "cost_usd": 0.001})
        return "Curve building completed at 14:23 on server1.", [], []

    with patch("app.routes.chat.run_agent", side_effect=_fake_run_agent):
        yield


@pytest.fixture
def mock_sidecar_http():
    """Mock httpx calls to sidecars using respx."""
    import respx
    import httpx
    with respx.mock(assert_all_called=False) as mock:
        mock.post("http://server1.stirt.internal:9000/search").mock(
            return_value=httpx.Response(200, json={
                "results": [{"path": "/opt/curve/logs/app.log", "matched_lines": [], "total_matched": 3, "error": None}],
                "total_files_searched": 1,
            })
        )
        yield mock
