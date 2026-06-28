# LogSight Agent

The central Python server. Traders send plain-English questions to it; it uses Claude to identify which registered processes are relevant, fans out log searches to sidecars on the appropriate machines in parallel, then uses Claude again to synthesize the results into a plain-English answer.

---

## Overview

- **Two-call LLM architecture** — one call routes the question (which processes, what keywords), a second call summarizes the raw log evidence into a readable answer.
- **Parallel fanout** — all sidecar queries for a single chat request run concurrently via `asyncio` + `httpx`.
- **Graceful degradation** — if a sidecar is unreachable, the agent notes it in the context sent to the summarization call and continues with whatever data it did collect.
- **Process registry** — PostgreSQL table stores which processes exist, where their sidecars are, and example Q&A pairs that improve routing accuracy.

---

## Setup

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and a running PostgreSQL instance.

```bash
cd agent

# Install dependencies (uv creates .venv automatically)
uv sync

# Configure
cp .env.example .env
# Edit .env: set LOGSIGHT_ANTHROPIC_API_KEY and LOGSIGHT_DATABASE_URL

# Run (dev mode with auto-reload)
uv run uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

On first startup the agent auto-creates the `processes` table if it does not exist.

---

## Configuration

All settings are read from environment variables (or a `.env` file in the `agent/` directory).

| Variable                    | Default                                                        | Description                       |
|-----------------------------|----------------------------------------------------------------|-----------------------------------|
| `LOGSIGHT_DATABASE_URL`     | `postgresql+asyncpg://logsight:logsight@localhost:5432/logsight` | Async SQLAlchemy connection URL   |
| `LOGSIGHT_ANTHROPIC_API_KEY`| —                                                              | **Required.** Anthropic API key   |
| `LOGSIGHT_HOST`             | `0.0.0.0`                                                      | Bind address                      |
| `LOGSIGHT_PORT`             | `8080`                                                         | Listen port                       |

The `postgresql+asyncpg://` scheme is required — the agent uses `asyncpg` for async I/O. Plain `postgresql://` (psycopg2) will not work.

---

## API Reference

Base URL: `http://<host>:8080`

---

### `GET /v1/health`

Liveness check.

**Response**

```json
{ "status": "ok", "version": "0.1.0" }
```

---

### `POST /v1/chat`

Submit a plain-English question and receive a plain-English answer synthesized from live log data.

**Request body**

```json
{ "question": "Is curve building complete for today?" }
```

| Field      | Type     | Required | Description                  |
|------------|----------|----------|------------------------------|
| `question` | `string` | yes      | Non-empty trader question    |

**Response body**

```json
{
  "answer": "Curve building completed at 14:23 on server1. It is still running on server2 as of 14:31.",
  "sources": [
    { "process": "CurveBuilder", "machine": "server1.prod", "files_searched": 2, "lines_matched": 7 },
    { "process": "CurveBuilder", "machine": "server2.prod", "files_searched": 2, "lines_matched": 3 }
  ]
}
```

| Field                      | Type     | Description                                                         |
|----------------------------|----------|---------------------------------------------------------------------|
| `answer`                   | `string` | Plain-English answer synthesized by Claude.                         |
| `sources`                  | `array`  | One entry per sidecar that was queried.                             |
| `sources[].process`        | `string` | Process name from the registry.                                     |
| `sources[].machine`        | `string` | Hostname of the machine that was searched.                          |
| `sources[].files_searched` | `integer`| Number of log files examined on that machine.                       |
| `sources[].lines_matched`  | `integer`| Total matching lines across all files on that machine.              |

**Error responses**

| Status | Condition                                                 |
|--------|-----------------------------------------------------------|
| `422`  | `question` is empty or missing                            |
| `502`  | LLM call failed (Anthropic API error or network issue)    |

**Example**

```bash
curl -s -X POST http://localhost:8080/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"question": "Any errors in the risk engine in the last hour?"}' | jq .
```

---

### `GET /v1/processes`

List all registered processes.

**Response** — array of process objects (see schema below).

```bash
curl http://localhost:8080/v1/processes | jq .
```

---

### `POST /v1/processes`

Register a new process.

**Request body**

```json
{
  "name": "CurveBuilder",
  "description": "Builds yield curves each morning using market data from Bloomberg",
  "machine_host": "server1.prod",
  "sidecar_port": 9000,
  "log_paths": [
    "/opt/app/logs/curve-builder.log",
    "/opt/app/logs/curve-builder-*.log"
  ],
  "example_qa": [
    {
      "question": "Is curve building complete?",
      "answer": "Look for 'Curve building completed' or 'all curves done' in the logs"
    }
  ]
}
```

| Field          | Type       | Required | Default | Description                                                               |
|----------------|------------|----------|---------|---------------------------------------------------------------------------|
| `name`         | `string`   | yes      | —       | Short display name                                                        |
| `description`  | `string`   | yes      | —       | Sentence describing what this process does; used for LLM routing          |
| `machine_host` | `string`   | yes      | —       | Hostname or IP the sidecar is running on                                  |
| `sidecar_port` | `integer`  | no       | `9000`  | Port the sidecar listens on                                               |
| `log_paths`    | `string[]` | yes      | —       | One or more paths/globs. These are sent directly to the sidecar's search. |
| `example_qa`   | `object[]` | no       | `[]`    | Q&A pairs that help the LLM recognize when to query this process          |

**Response** — `201 Created` with the created process object including its assigned `id`.

---

### `PUT /v1/processes/{id}`

Update an existing process. All fields are optional — only supplied fields are changed.

```bash
curl -X PUT http://localhost:8080/v1/processes/550e8400-e29b-41d4-a716-446655440000 \
  -H 'Content-Type: application/json' \
  -d '{"sidecar_port": 9001}'
```

**Response** — updated process object.

| Status | Condition              |
|--------|------------------------|
| `404`  | Process ID not found   |

---

### `DELETE /v1/processes/{id}`

Remove a process from the registry.

```bash
curl -X DELETE http://localhost:8080/v1/processes/550e8400-e29b-41d4-a716-446655440000
```

**Response** — `204 No Content`

| Status | Condition              |
|--------|------------------------|
| `404`  | Process ID not found   |

---

### Process object schema

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "CurveBuilder",
  "description": "Builds yield curves each morning",
  "machine_host": "server1.prod",
  "sidecar_port": 9000,
  "log_paths": ["/opt/app/logs/curve-builder.log"],
  "example_qa": [
    { "question": "Is curve building complete?", "answer": "Look for 'completed' in logs" }
  ],
  "created_at": "2024-01-15T09:00:00",
  "updated_at": "2024-01-15T09:00:00"
}
```

---

## Architecture

### Request lifecycle — `POST /v1/chat`

```
Trader question
      │
      ▼
① identify_processes(question, all_registered_processes)
   → Claude analyzes the question and the registry descriptions
   → Returns: relevant_process_ids[], keywords[]
      │
      ▼
② fanout_search(targets, keywords)
   → One asyncio task per relevant process/machine pair
   → Each task: POST http://<host>:<port>/search  (10s timeout)
   → Unreachable sidecars: captured as error, not raised
      │
      ▼
③ summarize_results(question, sidecar_results)
   → Claude receives: question + all log snippets + unreachable notices
   → Returns: plain-English answer
      │
      ▼
ChatResponse { answer, sources[] }
```

### LLM call 1 — `identify_processes`

**Input:** trader question + JSON array of all processes (id, name, description, example_qa)

**Output (JSON):**
```json
{
  "relevant_process_ids": ["uuid-a", "uuid-b"],
  "keywords": ["curve", "building", "complete", "finished"]
}
```

The process descriptions and example Q&A pairs are the primary signal Claude uses to route the question. Well-written descriptions significantly improve routing accuracy.

### LLM call 2 — `summarize_results`

**Input:** trader question + collected log snippets formatted as:

```
[CurveBuilder @ server1.prod] /opt/app/logs/curve-builder.log (5 matches):
  L1234: 2024-01-15 14:23:01 INFO Curve building completed
  L1235: 2024-01-15 14:23:01 INFO All 47 curves done

[CurveBuilder @ server2.prod] UNREACHABLE: Timeout connecting to server2.prod:9000
```

**Output:** plain-English answer string.

---

## Database schema

```sql
CREATE TABLE processes (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,
    description  TEXT NOT NULL,
    machine_host TEXT NOT NULL,
    sidecar_port INTEGER DEFAULT 9000,
    log_paths    TEXT[] NOT NULL,
    example_qa   JSONB DEFAULT '[]',
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);
```

`example_qa` stores an array of `{"question": "...", "answer": "..."}` objects. These are passed verbatim to Claude during routing so it can recognize domain-specific phrasings.

The schema is created automatically at startup via SQLAlchemy's `create_all` — no migration tool is required for the current single-table schema.

---

## Source layout

```
agent/
├── main.py                    — FastAPI app, lifespan (DB init), static mounts, root redirect
├── pyproject.toml             — uv project manifest and dependencies
├── .env.example
├── Dockerfile
│
├── app/
│   ├── config.py              — pydantic-settings; reads LOGSIGHT_* env vars / .env
│   ├── schemas.py             — Pydantic request/response models (ChatRequest, ProcessCreate, etc.)
│   │
│   ├── db/
│   │   ├── models.py          — SQLAlchemy ORM: Process table
│   │   └── database.py        — async engine, session factory, get_db dependency, init_db
│   │
│   ├── routes/
│   │   ├── chat.py            — POST /v1/chat: orchestrates the full routing→fanout→summarize flow
│   │   └── processes.py       — GET/POST/PUT/DELETE /v1/processes
│   │
│   └── services/
│       ├── llm.py             — identify_processes() and summarize_results() using anthropic SDK
│       └── fanout.py          — fanout_search(): parallel httpx queries to sidecars
│
└── ui/
    ├── chat/index.html        — Trader chat interface (served at /ui/chat/)
    └── admin/index.html       — Admin process registration UI (served at /ui/admin/)
```

---

## Dependencies

| Package             | Version  | Purpose                                    |
|---------------------|----------|--------------------------------------------|
| `fastapi`           | 0.115    | Web framework, routing, dependency injection|
| `uvicorn[standard]` | 0.30     | ASGI server                                |
| `sqlalchemy[asyncio]`| 2.0     | Async ORM, schema management               |
| `asyncpg`           | 0.29     | Async PostgreSQL driver                    |
| `httpx`             | 0.27     | Async HTTP client for sidecar fanout       |
| `anthropic`         | 0.34     | Anthropic Python SDK                       |
| `pydantic-settings` | 2.5      | `.env` / environment variable config       |

---

## Running in production

```bash
# Without Docker
uv run uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4

# With Docker (see deploy/)
docker-compose up -d agent
```

For production, run behind a reverse proxy (nginx/caddy) that handles TLS. The agent itself does not terminate TLS in Phase 1.
