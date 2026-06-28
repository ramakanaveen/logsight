# LogSight

Distributed log intelligence for trading firms. Instead of SSHing into machines to grep logs manually, traders ask plain-English questions through a chat interface. An LLM agent fans out queries to lightweight sidecars running on each machine, collects log snippets, and returns a plain-English summary.

```
Trader: "Is curve building complete for today?"
→ Agent identifies CurveBuilder processes
→ Queries sidecars on server1, server2 in parallel
→ Claude summarizes: "Curve building completed at 14:23 on server1, still running on server2"
```

---

## Quick start (local — no Docker)

Prerequisites: Rust, [uv](https://docs.astral.sh/uv/), PostgreSQL running locally.

```bash
git clone <repo-url> && cd logsight

# 1. Build the sidecar
cd sidecar && cargo build --release && cd ..

# 2. Create the database
psql -U postgres -c "CREATE USER logsight WITH PASSWORD 'logsight';"
psql -U postgres -c "CREATE DATABASE logsight OWNER logsight;"

# 3. Configure and install agent dependencies
cd agent
cp .env.example .env
# Edit .env — set LOGSIGHT_ANTHROPIC_API_KEY and adjust DATABASE_URL if needed
uv sync

# 4. Start both services (each in its own terminal)
../sidecar/target/release/logsight-sidecar --port 9000
uv run uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# 5. Verify
curl http://localhost:9000/health
curl http://localhost:8080/v1/health
```

Open in browser:
- Trader chat: http://localhost:8080/ui/chat/
- Admin panel: http://localhost:8080/ui/admin/

## Quick start (Docker Compose)

```bash
# Clone and enter the repo
git clone <repo-url> && cd logsight

# Set your Anthropic API key
export LOGSIGHT_ANTHROPIC_API_KEY=sk-ant-...

# Start agent + postgres
cd deploy && docker-compose up -d

# Open in browser
open http://localhost:8080/ui/chat/   # Trader chat
open http://localhost:8080/ui/admin/  # Register processes
```

---

## Components

| Component | Language | Location | Documentation |
|-----------|----------|----------|---------------|
| **Sidecar** | Rust | `sidecar/` | [`sidecar/README.md`](sidecar/README.md) |
| **Agent** | Python + FastAPI | `agent/` | [`agent/README.md`](agent/README.md) |
| **UIs** | Vanilla HTML/JS | `agent/ui/` | [`agent/ui/README.md`](agent/ui/README.md) |
| **Deploy** | Docker / systemd | `deploy/` | [`deploy/README.md`](deploy/README.md) |

---

## Architecture

```
[Trader Chat /ui/chat]     [Admin UI /ui/admin]
          │                        │
          └────────────┬───────────┘
                       ▼
          [Central Agent — Python FastAPI :8080]
            ① Claude: route question → which processes + keywords
            ② Parallel fanout to sidecars (asyncio + httpx)
            ③ Claude: synthesize log snippets → plain-English answer
            └── PostgreSQL: process registry
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
  [Sidecar        [Sidecar        [Sidecar
   server1:9000]   server2:9000]   host-N:9000]
   reads *.log     reads *.log     reads *.log
```

---

## Project structure

```
logsight/
├── CLAUDE.md                        ← project specification
├── README.md                        ← this file
│
├── sidecar/                         ← Rust binary (runs on every machine)
│   ├── Cargo.toml
│   ├── README.md
│   └── src/
│       ├── main.rs
│       ├── config.rs
│       ├── api.rs
│       └── search.rs
│
├── agent/                           ← Python FastAPI (central server)
│   ├── main.py
│   ├── pyproject.toml               ← uv project manifest and dependencies
│   ├── Dockerfile
│   ├── README.md
│   ├── ui/
│   │   ├── README.md
│   │   ├── chat/index.html
│   │   └── admin/index.html
│   └── app/
│       ├── config.py
│       ├── schemas.py
│       ├── db/
│       │   ├── database.py
│       │   └── models.py
│       └── routes/ + services/
│
└── deploy/
    ├── README.md
    ├── docker-compose.yml
    └── logsight-sidecar.service
```

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Sidecar | Rust · tokio · axum |
| Agent | Python 3.11+ · FastAPI · asyncio · uv |
| LLM | Anthropic Claude (`claude-sonnet-4-6`) |
| Database | PostgreSQL · SQLAlchemy async · asyncpg |
| HTTP client (fanout) | httpx |
| UI | Vanilla HTML/CSS/JS |
| Deployment | systemd (Linux) · Docker Compose |

---

## Development checklist (Phase 1)

- [x] Rust sidecar: `/health` + `/search` with glob support
- [x] Python agent: process registry CRUD
- [x] Claude integration: routing + summarization
- [x] Trader chat UI
- [x] Admin process registration UI
- [x] Systemd unit file + Docker Compose

## Planned (Phase 2)

- [ ] Auth token between agent and sidecars
- [ ] TLS for sidecar endpoints
- [ ] Elasticsearch query backend (instead of raw file grep)
- [ ] Windows Event Log support in sidecar
- [ ] Streaming responses in chat UI
