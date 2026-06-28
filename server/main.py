import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update

from app.config import settings
from app.db.database import engine, AsyncSessionLocal
from app.db.models import SidecarInstance
from app.routes.chat import router as chat_router
from app.routes.processes import router as processes_router
from app.routes.topology import router as topology_router
from app.routes.conversations import router as conversations_router


async def _mark_dead_sidecars() -> None:
    """Background task: mark sidecars dead if last_heartbeat is older than heartbeat_timeout."""
    while True:
        await asyncio.sleep(30)
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=settings.heartbeat_timeout)
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(SidecarInstance)
                .where(SidecarInstance.last_heartbeat < cutoff, SidecarInstance.status == "alive")
                .values(status="dead")
            )
            await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_mark_dead_sidecars())
    yield
    task.cancel()


app = FastAPI(title="LogSight Server", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(processes_router)
app.include_router(topology_router)
app.include_router(conversations_router)


@app.get("/v1/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}
