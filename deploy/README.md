# LogSight Deployment

---

## Docker Compose (recommended for development / single-host)

Runs PostgreSQL, the Python agent, and a placeholder sidecar container together.

### Prerequisites

- Docker 24+ and Docker Compose v2
- An Anthropic API key

### Steps

```bash
cd deploy

# Set your API key (do not commit this)
export LOGSIGHT_ANTHROPIC_API_KEY=sk-ant-...

# Start everything
docker-compose up -d

# Tail logs
docker-compose logs -f agent

# Stop
docker-compose down
```

Open:
- Chat: http://localhost:8080/ui/chat/
- Admin panel: http://localhost:8080/ui/admin/

### Services defined in `docker-compose.yml`

| Service           | Port(s)    | Description                                                    |
|-------------------|------------|----------------------------------------------------------------|
| `postgres`        | 5432       | PostgreSQL 16. Data persisted in `pgdata` Docker volume.       |
| `agent`           | 8080       | Python FastAPI agent. Waits for postgres to be healthy first.  |
| `sidecar-example` | 9000       | **Placeholder only** — replace with the real sidecar binary.   |

The agent's `DATABASE_URL` is hard-wired to reach `postgres` by service name inside the compose network. The `LOGSIGHT_ANTHROPIC_API_KEY` is passed through from the host environment.

### Replacing the placeholder sidecar

The `sidecar-example` service is a stub. To run a real sidecar in Docker:

1. Build the sidecar binary for Linux:
   ```bash
   cd ../sidecar
   cross build --release --target x86_64-unknown-linux-musl
   ```

2. Replace the `sidecar-example` service in `docker-compose.yml`:
   ```yaml
   sidecar-example:
     image: alpine:3.19
     command: ["/logsight-sidecar", "--port", "9000"]
     volumes:
       - /var/log:/var/log:ro
       - ./logsight-sidecar:/logsight-sidecar:ro
     ports:
       - "9000:9000"
   ```
   Where `./logsight-sidecar` is the path to the compiled binary.

3. Register the sidecar via the admin UI with `machine_host: sidecar-example` (Docker service name) and port `9000`.

---

## Production deployment — multiple machines

In production each target machine runs the sidecar as a systemd service; the agent runs on a dedicated server (or container) with access to the database.

### Architecture

```
[Agent server]  ─────────────────────────────────────┐
  port 8080                                           │
  → PostgreSQL (same host or managed DB)              │
  → sidecars on target machines via HTTP              │
                                                      │
[Machine A: server1.prod]                             │
  logsight-sidecar  port 9000  ←────────────────── (agent fans out here)
  reads /opt/app/logs/*.log

[Machine B: server2.prod]
  logsight-sidecar  port 9000  ←────────────────── (agent fans out here)
  reads /var/log/risk-engine.log
```

### Installing the sidecar on a target machine

```bash
# On the agent build machine:
cross build --release --target x86_64-unknown-linux-musl
scp target/x86_64-unknown-linux-musl/release/logsight-sidecar server1.prod:/tmp/

# On server1.prod:
sudo mv /tmp/logsight-sidecar /usr/local/bin/logsight-sidecar
sudo chmod +x /usr/local/bin/logsight-sidecar

# Create system user
sudo useradd -r -s /bin/false logsight

# Grant read access to log directories
sudo setfacl -R -m u:logsight:rX /opt/app/logs   # if ACLs available
# or add logsight to the app group:
sudo usermod -aG appgroup logsight

# Install and start the systemd service
sudo cp logsight-sidecar.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now logsight-sidecar

# Verify
curl http://server1.prod:9000/health
```

### `logsight-sidecar.service`

```ini
[Unit]
Description=LogSight Sidecar
After=network.target

[Service]
Type=simple
User=logsight
ExecStart=/usr/local/bin/logsight-sidecar --port 9000
Restart=on-failure
RestartSec=5s
Environment=RUST_LOG=logsight=info

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadOnlyPaths=/opt/app/logs /var/log

[Install]
WantedBy=multi-user.target
```

Adjust `ReadOnlyPaths` to list the actual log directories on each machine. systemd will refuse reads from any path not listed, which limits blast radius if the sidecar is ever compromised.

### Agent in production

Requires [uv](https://docs.astral.sh/uv/) on the agent server (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

```bash
# On the agent server
cd agent

# Install dependencies (uv creates .venv automatically)
uv sync

# Create .env
cat > .env <<EOF
LOGSIGHT_DATABASE_URL=postgresql+asyncpg://logsight:<password>@<db-host>:5432/logsight
LOGSIGHT_ANTHROPIC_API_KEY=sk-ant-...
LOGSIGHT_HOST=0.0.0.0
LOGSIGHT_PORT=8080
EOF

# Run with multiple workers (for concurrent chat requests)
uv run uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4
```

Or use a systemd service:

```ini
[Unit]
Description=LogSight Agent
After=network.target postgresql.service

[Service]
Type=simple
User=logsight
WorkingDirectory=/opt/logsight/agent
ExecStart=/home/logsight/.local/bin/uv run uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4
Restart=on-failure
EnvironmentFile=/opt/logsight/agent/.env

[Install]
WantedBy=multi-user.target
```

---

## Network access requirements

| Source        | Destination            | Port | Protocol |
|---------------|------------------------|------|----------|
| Agent server  | Each sidecar machine   | 9000 | TCP/HTTP |
| Agent server  | PostgreSQL             | 5432 | TCP      |
| User browser| Agent server           | 8080 | TCP/HTTP |
| Agent server  | api.anthropic.com      | 443  | TCP/HTTPS|

Block direct user-browser access to port 9000 on sidecar machines — users should only interact with the agent.

---

## PostgreSQL setup

```sql
-- Run as postgres superuser
CREATE USER logsight WITH PASSWORD 'choose-a-strong-password';
CREATE DATABASE logsight OWNER logsight;
```

The agent creates the `processes` table automatically on first start. No migration scripts are needed for the current schema.

For a managed database (AWS RDS, GCP Cloud SQL, Azure Database for PostgreSQL), use the same connection URL format:

```
postgresql+asyncpg://logsight:<password>@<endpoint>:5432/logsight
```

---

## Upgrading

### Sidecar

The sidecar is stateless — upgrade by replacing the binary and restarting the service:

```bash
sudo systemctl stop logsight-sidecar
sudo cp new-logsight-sidecar /usr/local/bin/logsight-sidecar
sudo systemctl start logsight-sidecar
```

### Agent

```bash
cd agent
git pull
uv sync
sudo systemctl restart logsight-agent
```

The agent creates new database columns automatically via `create_all`. For destructive schema changes (column renames, drops), apply them manually before restarting.

---

## Health checks

```bash
# Sidecar on server1
curl http://server1.prod:9000/health

# Agent
curl http://agent.internal:8080/v1/health

# PostgreSQL connectivity (from agent host)
psql postgresql://logsight:<password>@<db-host>:5432/logsight -c "SELECT 1"
```
