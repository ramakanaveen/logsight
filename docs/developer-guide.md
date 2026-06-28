# LogSight Developer Guide

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| [uv](https://docs.astral.sh/uv/) | latest | Python dependency management |
| [Node.js](https://nodejs.org/) | 18+ | React UI |
| [Rust](https://rustup.rs/) | stable | Sidecar binary |
| [PostgreSQL](https://postgresql.org/) | 14+ | Server database |
| [Docker](https://docker.com/) | optional | Full stack via Compose |

---

## Quick Start (local dev)

### 1. Database

```bash
psql -U postgres -c "CREATE USER logsight WITH PASSWORD 'logsight';"
psql -U postgres -c "CREATE DATABASE logsight OWNER logsight;"
```

### 2. Server

```bash
cd server
cp .env.example .env
# Fill in LOGSIGHT_DB_PASSWORD and LOGSIGHT_ANTHROPIC_API_KEY

uv sync                                          # install dependencies
LOGSIGHT_ENV=dev uv run alembic upgrade head     # run all migrations
uv run uvicorn main:app --port 8080 --reload     # start server
```

### 3. UI

```bash
cd ui
npm install
npm run dev     # starts at :5173, proxies /v1/* → :8080
```

### 4. Sidecar (optional for local testing)

```bash
cd sidecar
cargo build --release
./target/release/logsight-sidecar \
  --port 9000 \
  --agent-url http://localhost:8080 \
  --machine-host myhost.local \
  --log-dir /var/log
```

---

## Project Structure

```
logsight/
├── docs/                       ← documentation (this directory)
├── sidecar/                    ← Rust binary
│   └── src/
│       ├── main.rs             ← startup, axum router
│       ├── config.rs           ← layered config (toml + env + CLI)
│       ├── api.rs              ← /health and /search handlers
│       └── search.rs           ← glob expansion, grep, time filtering
├── server/                     ← Python FastAPI
│   ├── main.py                 ← app factory, router registration, lifespan
│   ├── pyproject.toml          ← uv manifest
│   ├── alembic/                ← database migrations
│   │   └── versions/           ← 001_initial … 005_feedback
│   ├── presentation/           ← stakeholder slide deck (served at /presentation)
│   └── app/
│       ├── config.py           ← pydantic-settings (LOGSIGHT_* env vars)
│       ├── schemas.py          ← pydantic request/response models
│       ├── db/
│       │   ├── database.py     ← async SQLAlchemy engine + get_db
│       │   └── models.py       ← ORM models
│       ├── routes/
│       │   ├── chat.py         ← POST /v1/chat/stream + /v1/chat
│       │   ├── conversations.py
│       │   ├── processes.py
│       │   ├── topology.py
│       │   └── feedback.py
│       └── services/
│           ├── agent.py        ← agentic loop (tool-use + extended thinking)
│           └── fanout.py       ← parallel httpx queries to sidecars
├── ui/                         ← React + Vite + TypeScript
│   └── src/
│       ├── api.ts              ← server API client
│       ├── types.ts            ← shared TypeScript types
│       ├── store.ts            ← Zustand global state
│       ├── hooks/useChat.ts    ← SSE stream consumer
│       ├── pages/
│       │   ├── ChatPage.tsx
│       │   └── AdminPage.tsx
│       └── components/
│           ├── MessageBubble.tsx
│           ├── ChartBlock.tsx
│           ├── ClarifyPrompt.tsx
│           ├── SourceChips.tsx
│           └── ConversationSidebar.tsx
└── deploy/
    ├── logsight-sidecar.service ← systemd unit file
    └── docker-compose.yml
```

---

## Database Migrations (Alembic)

All schema changes go through Alembic. The project uses PostgreSQL in production and SQLite for tests.

```bash
cd server

# Apply all pending migrations
LOGSIGHT_ENV=dev uv run alembic upgrade head

# Rollback one migration
LOGSIGHT_ENV=dev uv run alembic downgrade -1

# Rollback to a specific revision
LOGSIGHT_ENV=dev uv run alembic downgrade 001

# Show current revision
LOGSIGHT_ENV=dev uv run alembic current

# Show migration history
LOGSIGHT_ENV=dev uv run alembic history
```

### Creating a new migration

```bash
# Auto-generate from model changes
LOGSIGHT_ENV=dev uv run alembic revision --autogenerate -m "Add my_table"

# Or create an empty migration
LOGSIGHT_ENV=dev uv run alembic revision -m "Custom migration"
```

Migration files live in `server/alembic/versions/`. Name them `NNN_description.py`.

**Important**: migrations 003 and 004 use PostgreSQL-specific types (UUID, JSONB, ARRAY). Use `CURRENT_TIMESTAMP` (not `NOW()`) in `server_default` for SQLite compatibility in tests.

---

## Configuration

### Server environment variables

All variables use the `LOGSIGHT_` prefix and are read by pydantic-settings.

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGSIGHT_ENV` | `dev` | Selects `config/{env}.ini` |
| `LOGSIGHT_DB_PASSWORD` | — | PostgreSQL password (secret) |
| `LOGSIGHT_ANTHROPIC_API_KEY` | — | Anthropic API key (secret) |
| `LOGSIGHT_HOST` | `0.0.0.0` | Server bind address |
| `LOGSIGHT_PORT` | `8080` | Server port |
| `LOGSIGHT_HEARTBEAT_TIMEOUT` | `60` | Seconds before sidecar marked dead |

Copy `.env.example` → `.env` and fill in secrets. `.env` is gitignored.

### Sidecar configuration

Priority order: CLI flags > env vars > `logsight.toml`.

```toml
# logsight.toml (next to binary)
port = 9000
log_dir = "/var/log"
```

| CLI flag | Env var | Description |
|----------|---------|-------------|
| `--port` | `LOGSIGHT_PORT` | Listen port |
| `--log-dir` | `LOGSIGHT_LOG_DIR` | Default log search directory |
| `--agent-url` | `LOGSIGHT_AGENT_URL` | Server URL for self-registration |
| `--machine-host` | `LOGSIGHT_MACHINE_HOST` | Hostname to register as |

---

## Running Tests

```bash
# Server (Python — runs against in-memory SQLite)
cd server && uv run pytest tests/ -v

# Single test file
cd server && uv run pytest tests/test_agent.py -v

# Sidecar (Rust)
cd sidecar && cargo test

# UI (Vitest)
cd ui && npm test -- --run
```

Test counts (Phase 3): **171 Python** · **28 Rust** · **42 Vitest**

### Test architecture

- **Unit tests** (`tests/test_*.py`): mock Anthropic client + in-memory SQLite via `create_all`
- **Integration tests** (`tests/integration/`): FastAPI `TestClient` + in-memory SQLite + mock `run_agent`
- **Migration tests** (`tests/test_migrations.py`): run Alembic against a temp SQLite file

---

## Adding a New Agent Tool

1. Add tool definition to the `TOOLS` list in `server/app/services/agent.py`
2. Handle it in `_execute_tool()` (or intercept before the call, like `render_chart`)
3. Update the system prompt if Claude needs guidance on when to use it
4. Add SSE event type to `ui/src/types.ts` if it emits a new event
5. Handle the event in `ui/src/hooks/useChat.ts`
6. Write a test in `server/tests/test_agent.py`

---

## Deployment

### Docker Compose (recommended for staging)

```bash
export LOGSIGHT_ANTHROPIC_API_KEY=sk-ant-...
cd deploy && docker-compose up -d
```

Includes: server + PostgreSQL + a placeholder sidecar. Edit `docker-compose.yml` to add real sidecar instances.

### Sidecar on Linux (systemd)

```bash
# Copy binary and config
scp sidecar/target/x86_64-unknown-linux-musl/release/logsight-sidecar server1:/opt/logsight/
scp deploy/logsight-sidecar.service /etc/systemd/system/

# Enable and start
systemctl daemon-reload
systemctl enable --now logsight-sidecar

# Check logs
journalctl -u logsight-sidecar -f
```

### Cross-compile sidecar for Linux

```bash
cargo install cross
cross build --release --target x86_64-unknown-linux-musl
# Binary: sidecar/target/x86_64-unknown-linux-musl/release/logsight-sidecar
```

---

## Roadmap

| Phase | Status | Items |
|-------|--------|-------|
| Phase 1 | ✅ Done | Sidecar, agent, process registry, chat UI, admin UI |
| Phase 2 | ✅ Done | Fleet topology, agentic loop, SSE streaming, conversation persistence, React UI |
| Phase 3 | ✅ Done | Markdown, charts, token tracking, feedback, source attribution, arbitrary log search |
| Phase 4 | Planned | Auth tokens between server↔sidecar, TLS, Elasticsearch integration, Windows Event Log, Playwright e2e |
