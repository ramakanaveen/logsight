from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.db.database import init_db
from app.routes.chat import router as chat_router
from app.routes.processes import router as processes_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="LogSight Agent", version="0.1.0", lifespan=lifespan)

app.include_router(chat_router)
app.include_router(processes_router)

app.mount("/ui/chat", StaticFiles(directory="ui/chat", html=True), name="chat-ui")
app.mount("/ui/admin", StaticFiles(directory="ui/admin", html=True), name="admin-ui")


@app.get("/v1/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/")
async def root():
    return RedirectResponse(url="/ui/chat/")
