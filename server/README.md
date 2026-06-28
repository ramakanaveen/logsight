# LogSight Server

The central Python server. Engineers and operators send plain-English questions; a Claude agentic loop uses tool-use + extended thinking to discover alive sidecars, search the right log files in parallel, and stream a plain-English answer via Server-Sent Events.

---

## Architecture

### Agentic loop (one request → multiple tool calls)

```
User question (SSE stream)
      │
      ▼
Claude (tool-use + extended thinking)
  ├── list_sidecars(namespace?, machine_host?, process_name?)
  │     → queries PostgreSQL SidecarInstance table
  │     → returns alive sidecars with their registered processes
  │
  ├── search_logs(sidecar_id, process_name, keywords, time_window_minutes?)
  │     → resolves log paths from MachineProcess registry
  │     → POSTs to sidecar /search endpoint
  │     → returns matched lines
  │
  └── ask_user(question, options?)
        → emits "clarify" SSE event → pauses loop
        → next chat turn resumes with user's reply
      │
      ▼
Claude synthesizes log evidence → streams answer
```

### SSE event catalogue

Each event is a `data: {...}\n\n` line with `type` and `data` fields:

| Event | When | Data |
|-------|------|------|
| `thinking` | Claude extended thinking block | `{ text }` |
| `tool_call` | Before each tool execution | `{ tool, input }` |
| `tool_result` | After each tool execution | `{ tool, result }` |
| `clarify` | `ask_user` tool called | `{ question, options? }` |
| `answer` | Claude final text block | `{ text }` |
| `sources` | After answer | `[{ process, machine, files_searched, lines_matched, matched_files }]` |
| `usage` | After answer | `{ input_tokens, output_tokens, total_tokens, cost_usd }` |
| `chart` | `render_chart` tool called | `{ chart_type, title, labels, datasets }` |
| `done` | Stream complete | `{ conversation_id, clarify? }` |
| `error` | Any exception | `{ message }` |

---

## Setup

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and PostgreSQL.

```bash
cd server

# Install dependencies
uv sync

# Configure
cp .env.example .env
# Edit .env — set LOGSIGHT_DB_PASSWORD and LOGSIGHT_ANTHROPIC_API_KEY

# Run migrations
LOGSIGHT_ENV=dev uv run alembic upgrade head

# Start (dev mode with auto-reload)
LOGSIGHT_ENV=dev uv run uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

---

## Configuration

### `config/{env}.ini`

Select environment with `LOGSIGHT_ENV` (default: `dev`).

```ini
[server]
host = 0.0.0.0
port = 8080
model = claude-sonnet-4-6

[database]
host = localhost
port = 5432
name = logsight
user = logsight
```

### `.env` (secrets only — gitignored)

```
LOGSIGHT_DB_PASSWORD=logsight
LOGSIGHT_ANTHROPIC_API_KEY=sk-ant-...
```

---

## Database migrations

```bash
# Apply all pending migrations
LOGSIGHT_ENV=dev uv run alembic upgrade head

# Check current revision
LOGSIGHT_ENV=dev uv run alembic current

# Create a new migration
LOGSIGHT_ENV=dev uv run alembic revision -m "describe_change"

# Rollback one step
LOGSIGHT_ENV=dev uv run alembic downgrade -1
```

### Migration history

| Revision | Description |
|----------|-------------|
| `001` | Initial schema (namespaces, machines, sidecar_instances, process_definitions, machine_processes) |
| `002` | Conversations + messages tables |
| `003` | Fix UUID columns from VARCHAR(36) to native PostgreSQL UUID |
| `004` | Fix JSONB (example_qa, metadata) and TEXT[] (log_paths) column types |

---

## API Reference

Base URL: `http://<host>:8080`

### Health

`GET /v1/health` → `{ "status": "ok", "version": "0.1.0" }`

---

### Chat

#### `POST /v1/chat/stream`

SSE streaming agentic loop. Emits events from the table above.

**Request body**
```json
{
  "question": "Is curve building complete for today?",
  "conversation_id": "uuid (optional — omit to start new conversation)",
  "process_hint": "CurveBuilder (optional — /process filter from UI)"
}
```

**Example**
```bash
curl -s -N -X POST http://localhost:8080/v1/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"question": "Any errors in the risk engine?"}' \
  | grep '^data:' | jq -r '.type + ": " + (.data.text // (.data | tostring))'
```

#### `POST /v1/chat`

Non-streaming (backward compat). Returns full answer after all tool calls complete.

```json
{
  "answer": "Curve building completed at 14:23 on server1.",
  "sources": [...],
  "conversation_id": "uuid"
}
```

---

### Conversations

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/conversations` | List all conversations |
| `GET` | `/v1/conversations/{id}` | Get conversation with messages |
| `DELETE` | `/v1/conversations/{id}` | Delete conversation |

---

### Process definitions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/processes` | List all process definitions |
| `POST` | `/v1/processes` | Create process definition |
| `PUT` | `/v1/processes/{id}` | Update process definition |
| `DELETE` | `/v1/processes/{id}` | Delete process definition |

**Process definition object**
```json
{
  "id": "uuid",
  "name": "CurveBuilder",
  "description": "Builds yield curves each morning using Bloomberg market data",
  "example_qa": [
    { "question": "Is curve building done?", "answer": "Look for 'completed' in logs" }
  ]
}
```

---

### Fleet topology

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/topology` | Full fleet: namespaces → machines → sidecars |
| `POST` | `/v1/topology/namespaces` | Create namespace |
| `POST` | `/v1/topology/machines` | Create machine |
| `POST` | `/v1/topology/heartbeat` | Sidecar self-registration + heartbeat |
| `GET` | `/v1/topology/sidecars` | List sidecar instances |
| `POST` | `/v1/topology/machine-processes` | Assign process + log paths to machine |
| `DELETE` | `/v1/topology/machine-processes/{id}` | Remove machine-process assignment |

**Heartbeat request** (sent by sidecar on startup and every 30s)
```json
{
  "machine_host": "server1.prod",
  "port": 9000,
  "version": "0.1.0"
}
```

---

### Feedback

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/feedback` | Submit thumbs up/down rating |
| `GET` | `/v1/feedback` | List all feedback (admin) |

**Feedback request**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "rating": 1,
  "comment": "Great answer!"
}
```
`rating`: `1` = thumbs up, `-1` = thumbs down.

---

## Database schema

```
namespaces          (id, name, description)
  └── machines      (id, namespace_id, hostname, description)
        └── sidecar_instances  (id, machine_id, port, status, last_heartbeat, version)
        └── machine_processes  (id, machine_id, process_definition_id, log_paths[])

process_definitions (id, name, description, example_qa[])

conversations       (id, title, created_at, updated_at)
  └── messages      (id, conversation_id, role, content, metadata, created_at)

feedback            (id, conversation_id, message_id, rating, comment, created_at)
```

---

## Source layout

```
server/
├── main.py                    ← FastAPI app, lifespan, router mounts
├── pyproject.toml             ← uv project manifest
├── alembic.ini                ← migration config
├── alembic/versions/          ← migration scripts 001-005
├── config/
│   ├── dev.ini
│   ├── staging.ini
│   └── prod.ini
└── app/
    ├── config.py              ← pydantic-settings + configparser
    ├── schemas.py             ← Pydantic request/response models
    ├── db/
    │   ├── models.py          ← SQLAlchemy ORM models
    │   └── database.py        ← async engine, get_db, init_db
    ├── routes/
    │   ├── chat.py            ← SSE streaming + backward-compat endpoint
    │   ├── processes.py       ← process definition CRUD
    │   ├── topology.py        ← fleet topology + heartbeat
    │   ├── conversations.py   ← conversation list/detail/delete
    │   └── feedback.py        ← feedback CRUD
    └── services/
        ├── agent.py           ← agentic loop: tool definitions + execution
        ├── fanout.py          ← async httpx sidecar queries
        └── llm.py             ← legacy two-call LLM functions (Phase 1 compat)
```

---

## Running tests

```bash
cd server
uv run pytest tests/ -v

# Single file
uv run pytest tests/test_agent.py -v

# Integration tests
uv run pytest tests/integration/ -v
```
