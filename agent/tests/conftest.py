import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Process
from app.db.database import get_db
from main import app


# In-memory SQLite engine for tests (no PostgreSQL required)
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


@pytest.fixture
def sample_process_payload():
    return {
        "name": "CurveBuilder",
        "description": "Builds yield curves each morning",
        "machine_host": "server1.prod",
        "sidecar_port": 9000,
        "log_paths": ["/opt/app/logs/curve.log"],
        "example_qa": [{"question": "Is curve done?", "answer": "Look for completed"}],
    }


@pytest.fixture
async def created_process(client, sample_process_payload):
    resp = await client.post("/v1/processes", json=sample_process_payload)
    assert resp.status_code == 201
    return resp.json()
