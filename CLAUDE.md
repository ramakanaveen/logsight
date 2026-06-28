# CLAUDE.md — LogSight

## What is LogSight?

LogSight is a distributed log intelligence system for trading firms. Instead of SSHing into machines to grep logs manually, traders ask plain-English questions through a chat interface. An LLM agent fans out queries to lightweight sidecars running on each machine, collects log snippets, and returns a plain-English summary.

### Example
```
Trader: "Is curve building complete for today?"
→ Agent identifies CurveBuilder processes
→ Queries sidecars on server1, server2 in parallel
→ Sidecars search /opt/app/logs/curve-builder.log
→ Claude summarizes: "Curve building completed at 14:23 on server1, still running on server2"
```

---

## Architecture (Phase 2)

```
[React UI — ui/  :5173 (dev)]
   /chat  — trader SSE streaming chat
   /admin — fleet topology + process definitions
          |
          ▼ (proxied to :8080 in dev; CORS in prod)
[Server — server/  Python FastAPI :8080]
   - Claude agentic loop (tool-use + extended thinking)
   - Conversation persistence (PostgreSQL)
   - Fleet topology: Namespace → Machine → SidecarInstance
   - Process definitions + MachineProcess log-path registry
   - Alembic migrations; config/{env}.ini + .env secrets
          |
       ┌──┴──────────┐
       ▼             ▼
  [Sidecar      [Sidecar      (one per machine, self-registers)
   machine-1]    machine-2]
   port 9000     port 9000
       |             |
  /opt/logs/*.log  /var/log/...
```

---

## Components

### 1. Rust Sidecar (`sidecar/`)
- Single static binary — no dependencies to install on target machines
- Listens on configurable port (default: 9000)
- **Read-only**: only reads files where it has filesystem read permission
- Config: `logsight.toml` file + env vars + CLI flags (CLI wins, then env, then file)
- Auto-starts via systemd unit file on Linux / Docker entrypoint in containers

**Endpoints:**
```
GET  /health   → { status, version, port }
POST /search   → search log files, return matching lines
```

**Search request:**
```json
{
  "keywords": ["curve", "building", "complete"],
  "log_paths": ["/opt/app/logs/*.log", "/var/log/curve-builder.log"],
  "time_window_minutes": 60,
  "max_lines": 50
}
```

**Search response:**
```json
{
  "results": [
    {
      "path": "/opt/app/logs/curve-builder.log",
      "matched_lines": [
        { "line_number": 1234, "content": "2024-01-15 14:23:01 INFO Curve building completed" }
      ],
      "total_matched": 5,
      "error": null
    }
  ],
  "total_files_searched": 1
}
```

### 2. Central Agent (`agent/`)
- Python + FastAPI, managed with **uv** (`pyproject.toml`)
- Uses Anthropic Claude API for two LLM calls per query:
  1. **Route**: which processes are relevant + what keywords to search
  2. **Summarize**: turn log snippets into a plain-English answer
- Fans out to sidecars in parallel (asyncio + httpx)
- Graceful degradation: if a sidecar is unreachable, notes it and continues

**API endpoints:**
```
POST   /v1/chat              ← trader sends question, gets answer
GET    /v1/processes         ← list all registered processes
POST   /v1/processes         ← register a new process
PUT    /v1/processes/{id}    ← update a process
DELETE /v1/processes/{id}    ← remove a process
GET    /v1/health
GET    /ui/chat/             ← serve trader chat UI
GET    /ui/admin/            ← serve admin UI
```

### 3. Process Registry (PostgreSQL)
```sql
CREATE TABLE processes (
    id           UUID PRIMARY KEY,
    name         TEXT NOT NULL,
    description  TEXT NOT NULL,
    machine_host TEXT NOT NULL,
    sidecar_port INTEGER DEFAULT 9000,
    log_paths    TEXT[] NOT NULL,
    example_qa   JSONB DEFAULT '[]',   -- [{"question": "...", "answer": "..."}]
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);
```

Table is created automatically on first agent startup via SQLAlchemy `create_all`.

### 4. Trader Chat UI (`agent/ui/chat/index.html`)
- Dark-themed chat bubble interface
- Sends `POST /v1/chat`, streams answer into a bubble
- Source chips below each answer show machine · process · lines matched

### 5. Admin UI (`agent/ui/admin/index.html`)
- Table of all registered processes
- Add/Edit modal with dynamic Q&A pair management
- Delete with browser confirmation dialog
- Toast notifications for success/error feedback

---

## Project Structure

```
logsight/
├── CLAUDE.md                        ← this file
├── README.md                        ← top-level overview and quick start
│
├── sidecar/                         ← Rust binary (runs on every machine)
│   ├── Cargo.toml
│   ├── README.md
│   └── src/
│       ├── main.rs                  ← startup, axum router, tokio runtime
│       ├── config.rs                ← toml + env + CLI layered config (clap derive)
│       ├── api.rs                   ← /health and /search axum handlers
│       └── search.rs                ← glob expansion, keyword grep, time filtering
│
├── agent/                           ← Python FastAPI (central server)
│   ├── main.py                      ← FastAPI app, lifespan DB init, static mounts
│   ├── pyproject.toml               ← uv project manifest and pinned dependencies
│   ├── .env.example                 ← template — copy to .env and fill in secrets
│   ├── Dockerfile
│   ├── README.md
│   ├── ui/
│   │   ├── README.md
│   │   ├── chat/index.html          ← trader chat interface
│   │   └── admin/index.html         ← process registration UI
│   └── app/
│       ├── config.py                ← pydantic-settings, reads LOGSIGHT_* env vars
│       ├── schemas.py               ← pydantic request/response models
│       ├── db/
│       │   ├── database.py          ← async SQLAlchemy engine, get_db, init_db
│       │   └── models.py            ← Process ORM model
│       ├── routes/
│       │   ├── chat.py              ← POST /v1/chat (route → fanout → summarize)
│       │   └── processes.py         ← CRUD /v1/processes
│       └── services/
│           ├── llm.py               ← identify_processes() + summarize_results()
│           └── fanout.py            ← parallel httpx queries to sidecars
│
└── deploy/
    ├── README.md
    ├── logsight-sidecar.service     ← systemd unit file (with hardening)
    └── docker-compose.yml           ← agent + postgres + placeholder sidecar
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Sidecar | Rust (tokio + axum 0.7), single static binary |
| Central Agent | Python 3.11+ · FastAPI 0.115 · uv |
| LLM | Anthropic Claude (`claude-sonnet-4-6`) |
| Database | PostgreSQL · SQLAlchemy 2.0 async · asyncpg 0.30+ |
| HTTP fanout | httpx (async, 10s timeout per sidecar) |
| UI | Vanilla HTML/CSS/JS — no framework, no build step |
| Deployment | systemd (Linux) · Docker Compose |

---

## Configuration

### Sidecar (`logsight.toml` next to binary)
```toml
port = 9000
log_dir = "/var/log"          # optional default search dir
# token = "secret"            # optional auth token (Phase 2)
```

Priority order: CLI flags > env vars > `logsight.toml`.
Env vars: `LOGSIGHT_PORT`, `LOGSIGHT_LOG_DIR`, `LOGSIGHT_TOKEN`.
CLI flags: `--port`, `--log-dir`, `--token`, `--config <path>`.

### Agent (`.env`)
```
LOGSIGHT_DATABASE_URL=postgresql+asyncpg://logsight:logsight@localhost:5432/logsight
LOGSIGHT_ANTHROPIC_API_KEY=sk-ant-...
LOGSIGHT_HOST=0.0.0.0
LOGSIGHT_PORT=8080
```

All variables are prefixed `LOGSIGHT_` and read by pydantic-settings. `.env` is gitignored; copy from `.env.example`.

---

## Development Phases

### Phase 1 — MVP ✅ Complete
- [x] Rust sidecar: `/health` + `/search` with glob and time-window support
- [x] Python agent: process registry CRUD
- [x] Claude integration: routing + summarization (two LLM calls per chat request)
- [x] Trader chat UI with source attribution chips
- [x] Admin UI with add/edit/delete and dynamic Q&A pairs
- [x] Systemd unit file + Docker Compose
- [x] Full documentation for all components

### Phase 2 ✅ Complete
- [x] One sidecar per machine (self-registration + heartbeat)
- [x] Fleet topology: Namespace → Machine → SidecarInstance
- [x] Alembic migrations (replaces `create_all`)
- [x] Config split: `config/{env}.ini` + `.env` secrets only
- [x] Agentic loop: Claude tool-use + extended thinking
- [x] SSE streaming chat (`POST /v1/chat/stream`)
- [x] Conversation persistence (multi-turn history)
- [x] React + Vite + Tailwind UI (`ui/`) with TypeScript
- [x] 125 Python tests + 28 Rust tests + 25 Vitest component tests

### Phase 3 — Future
- [ ] Auth token between server and sidecars (LOGSIGHT_TOKEN)
- [ ] TLS for sidecar endpoints
- [ ] Elasticsearch integration (query ES index instead of raw file grep)
- [ ] Windows Event Log support in sidecar
- [ ] Playwright e2e tests

---

## Build & Run

### Sidecar
```bash
cd sidecar
cargo build --release
# Binary at: target/release/logsight-sidecar

./target/release/logsight-sidecar --port 9000 --log-dir /var/log
```

Cross-compile for Linux (required for deployment to Linux machines from macOS):
```bash
cargo install cross
cross build --release --target x86_64-unknown-linux-musl
```

### Server

Requires [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

```bash
cd server
cp .env.example .env                  # fill in LOGSIGHT_DB_PASSWORD and LOGSIGHT_ANTHROPIC_API_KEY
uv sync
LOGSIGHT_ENV=dev uv run alembic upgrade head   # run migrations (replaces create_all)
uv run uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### UI (React + Vite)

```bash
cd ui
npm install
npm run dev     # starts at :5173, proxies /v1/* to :8080
```

### PostgreSQL (local dev)
```bash
psql -U postgres -c "CREATE USER logsight WITH PASSWORD 'logsight';"
psql -U postgres -c "CREATE DATABASE logsight OWNER logsight;"
```

### Docker Compose (everything)
```bash
export LOGSIGHT_ANTHROPIC_API_KEY=sk-ant-...
cd deploy && docker-compose up -d
```

Open: http://localhost:5173/chat  — trader chat (dev)
Open: http://localhost:5173/admin — admin panel (dev)

---

## Test Commands

```bash
# Server (Python)
cd server && uv run pytest tests/ -v

# Sidecar (Rust)
cd sidecar && cargo test

# UI (Vitest)
cd ui && npm test
```

---

## Verification Checklist
1. `curl http://localhost:9000/health` → `{"status":"ok","version":"0.1.0","port":9000}`
2. `curl http://localhost:8080/v1/health` → `{"status":"ok","version":"0.1.0"}`
3. `LOGSIGHT_ENV=dev uv run alembic upgrade head` → all 7 tables created
4. Sidecar starts with `--agent-url http://localhost:8080 --machine-host server1` → self-registers → `GET /v1/topology` shows it alive
5. Create namespace + machine + process definitions in admin UI; assign processes with log paths
6. Ask a question in chat UI → SSE stream shows thinking → tool calls → answer
