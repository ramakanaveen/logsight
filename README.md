# LogSight

Distributed log intelligence for trading firms. Instead of SSHing into machines to grep logs manually, traders ask plain-English questions through a chat interface. A Claude agentic loop fans out queries to lightweight sidecars running on each machine, collects log snippets, and streams a plain-English summary back in real time.

```
Trader: "Is curve building complete for today?"
→ Agent lists alive sidecars → searches CurveBuilder logs in parallel
→ Claude streams: "Curve building completed at 14:23 on server1, still running on server2"
```

---

## Architecture (Phase 2)

```
[React UI — ui/  :5173 (dev)]
   /chat  — trader SSE streaming chat
   /admin — fleet topology + process definitions
          |
          ▼ (proxied to :8080 in dev)
[Server — server/  Python FastAPI :8080]
   - Claude agentic loop (tool-use + extended thinking)
   - Conversation persistence (PostgreSQL)
   - Fleet topology: Namespace → Machine → SidecarInstance
   - Process definitions + MachineProcess log-path registry
   - Alembic migrations
          |
       ┌──┴──────────┐
       ▼             ▼
  [Sidecar      [Sidecar      (one per machine, self-registers + heartbeat)
   machine-1]    machine-2]
   port 9000     port 9000
       |             |
  /opt/logs/*.log  /var/log/...
```

---

## Quick start (local)

Prerequisites: Rust, [uv](https://docs.astral.sh/uv/), Node 18+, PostgreSQL running locally.

```bash
git clone <repo-url> && cd logsight

# 1. Build the sidecar
cd sidecar && cargo build --release && cd ..

# 2. Create the database
psql -U postgres -c "CREATE USER logsight WITH PASSWORD 'logsight';"
psql -U postgres -c "CREATE DATABASE logsight OWNER logsight;"

# 3. Configure and install server dependencies
cd server
cp .env.example .env
# Edit .env — set LOGSIGHT_DB_PASSWORD and LOGSIGHT_ANTHROPIC_API_KEY
uv sync
LOGSIGHT_ENV=dev uv run alembic upgrade head

# 4. Start the server (terminal 1)
LOGSIGHT_ENV=dev uv run uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# 5. Start the UI (terminal 2)
cd ui && npm install && npm run dev

# 6. Start a sidecar on this machine (terminal 3)
./sidecar/target/release/logsight-sidecar \
  --port 9000 \
  --agent-url http://localhost:8080 \
  --machine-host localhost

# 7. Verify
curl http://localhost:9000/health
curl http://localhost:8080/v1/health
```

Open in browser:
- Trader chat: http://localhost:5173/chat
- Admin panel: http://localhost:5173/admin

## Quick start (Docker Compose)

```bash
export LOGSIGHT_ANTHROPIC_API_KEY=sk-ant-...
cd deploy && docker-compose up -d
```

Open: http://localhost:5173/chat

---

## Components

| Component | Language | Location | Documentation |
|-----------|----------|----------|---------------|
| **Server** | Python + FastAPI | `server/` | [`server/README.md`](server/README.md) |
| **React UI** | TypeScript + Vite | `ui/` | [`ui/README.md`](ui/README.md) |
| **Sidecar** | Rust | `sidecar/` | [`sidecar/README.md`](sidecar/README.md) |
| **Deploy** | Docker / systemd | `deploy/` | [`deploy/README.md`](deploy/README.md) |

---

## Project structure

```
logsight/
├── CLAUDE.md                        ← project specification
├── README.md                        ← this file
│
├── server/                          ← Python FastAPI central server
│   ├── main.py
│   ├── pyproject.toml               ← uv project manifest
│   ├── alembic/                     ← database migrations
│   ├── config/                      ← env-specific .ini files
│   └── app/
│       ├── config.py
│       ├── schemas.py
│       ├── db/                      ← SQLAlchemy models + engine
│       ├── routes/                  ← chat, processes, topology, conversations
│       └── services/                ← agent loop, fanout, llm
│
├── ui/                              ← React + Vite + Tailwind frontend
│   ├── src/
│   │   ├── pages/                   ← ChatPage, AdminPage
│   │   ├── components/              ← MessageBubble, SourceChips, etc.
│   │   ├── hooks/                   ← useChat
│   │   ├── store.ts                 ← Zustand store
│   │   └── api.ts                   ← SSE streaming + REST calls
│   └── vite.config.ts
│
├── sidecar/                         ← Rust binary (runs on every machine)
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs
│       ├── config.rs
│       ├── api.rs
│       ├── search.rs
│       └── registration.rs          ← self-registration + heartbeat
│
└── deploy/
    ├── docker-compose.yml
    └── logsight-sidecar.service
```

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Sidecar | Rust · tokio · axum — single static binary |
| Server | Python 3.11+ · FastAPI · asyncio · uv |
| LLM | Anthropic Claude (`claude-sonnet-4-6`) — tool-use + extended thinking |
| Database | PostgreSQL · SQLAlchemy 2.0 async · asyncpg · Alembic |
| HTTP fanout | httpx (async, 10s timeout per sidecar) |
| React UI | TypeScript · Vite · Tailwind CSS · Zustand · React Router |
| Deployment | systemd (Linux) · Docker Compose |

---

## Test commands

```bash
# Server (Python)
cd server && uv run pytest tests/ -v

# Sidecar (Rust)
cd sidecar && cargo test

# UI (Vitest)
cd ui && npm test
```

---

## Feature checklist

### Phase 1 ✅
- Rust sidecar: `/health` + `/search` with glob + time-window
- Python agent: process registry CRUD
- Two-LLM-call architecture (route → fanout → summarize)
- Trader chat UI + Admin UI (vanilla HTML)
- systemd unit file + Docker Compose

### Phase 2 ✅
- Sidecar self-registration + heartbeat
- Fleet topology: Namespace → Machine → SidecarInstance → MachineProcess
- Alembic migrations (replaces `create_all`)
- Config split: `config/{env}.ini` + `.env` secrets
- Agentic loop: Claude tool-use + extended thinking
- SSE streaming chat (`POST /v1/chat/stream`)
- Conversation persistence + multi-turn history
- React + Vite + Tailwind UI with TypeScript
- 125 Python tests · 28 Rust tests · 25 Vitest tests

### Phase 3 (in progress)
- Arbitrary log file search (user-specified paths)
- Proactive shutdown/anomaly detection
- Source file attribution (which files matched)
- Token usage tracking + display
- Markdown rendering in chat
- Process chooser buttons for ambiguous queries
- Charts (recharts bar/line/pie)
- Downloadable analysis export
- Feedback mechanism (👍👎)
- Integration tests
