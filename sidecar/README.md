# LogSight Sidecar

A lightweight, statically-linked Rust binary that runs on every machine you want to monitor. It exposes a small HTTP API over which the central server can search log files, and self-registers with the server on startup with periodic heartbeats.

---

## Overview

- **Read-only** — only reads files where it has filesystem permissions; never writes.
- **Zero dependencies** — single binary, no runtime libraries required.
- **Glob-aware** — log paths can include `*` and `**` patterns.
- **Time-windowed search** — limits matches to logs written within the last N minutes.
- **Self-registration** — on startup, POSTs to the server's `/v1/topology/heartbeat` endpoint and repeats every 30 seconds.

---

## Building

Requires Rust 1.75+ (install via [rustup](https://rustup.rs)).

```bash
cd sidecar

# Release build (optimized)
cargo build --release

# Binary location
./target/release/logsight-sidecar
```

Cross-compile for Linux from macOS (required for deployment to Linux machines):

```bash
cargo install cross
cross build --release --target x86_64-unknown-linux-musl
```

The `musl` target produces a fully static binary with no glibc dependency — deploy to any Linux machine without installing Rust.

---

## Configuration

Configuration is read from three sources in priority order (highest wins):

```
CLI flags  >  environment variables  >  logsight.toml file
```

### `logsight.toml`

Place this file next to the binary (or specify `--config <path>`):

```toml
port = 9000
log_dir = "/var/log"        # optional: default search directory
agent_url = "http://server:8080"  # central server for self-registration
machine_host = "server1.prod"     # how this machine identifies itself to the server
# token = "secret"          # auth token (Phase 3)
```

### Environment variables

| Variable              | Default | Description                                  |
|-----------------------|---------|----------------------------------------------|
| `LOGSIGHT_PORT`       | `9000`  | Port to listen on                            |
| `LOGSIGHT_LOG_DIR`    | —       | Default log directory hint                   |
| `LOGSIGHT_AGENT_URL`  | —       | Central server URL for self-registration     |
| `LOGSIGHT_MACHINE_HOST` | —     | Hostname to register as (defaults to OS hostname) |
| `LOGSIGHT_TOKEN`      | —       | Auth token                                   |

### CLI flags

```
logsight-sidecar [OPTIONS]

Options:
      --port <PORT>              Port to listen on [env: LOGSIGHT_PORT]
      --log-dir <LOG_DIR>        Default log directory [env: LOGSIGHT_LOG_DIR]
      --agent-url <AGENT_URL>    Central server URL [env: LOGSIGHT_AGENT_URL]
      --machine-host <HOST>      Hostname to register as [env: LOGSIGHT_MACHINE_HOST]
      --token <TOKEN>            Auth token [env: LOGSIGHT_TOKEN]
      --config <CONFIG>          Path to config file [default: logsight.toml]
  -h, --help                     Print help
```

---

## Running

```bash
# Minimal — no self-registration
./logsight-sidecar --port 9000

# With self-registration (recommended)
./logsight-sidecar \
  --port 9000 \
  --agent-url http://logsight-server:8080 \
  --machine-host server1.prod

# Using environment variables
LOGSIGHT_AGENT_URL=http://logsight-server:8080 \
LOGSIGHT_MACHINE_HOST=server1.prod \
./logsight-sidecar
```

Set `RUST_LOG=logsight=debug` for verbose logging.

---

## Self-registration flow

When `--agent-url` is provided:

1. On startup: POST `http://<agent-url>/v1/topology/heartbeat` with `{ machine_host, port, version }`
2. Server creates or updates the `SidecarInstance` record, sets `status = "alive"`, records `last_heartbeat`
3. Every 30 seconds: repeat the heartbeat POST
4. If the server marks a sidecar as dead (no heartbeat for > 60s), the agentic loop skips it

Without `--agent-url`, the sidecar still serves `/health` and `/search` normally — it just won't appear in the server's topology until you add it manually via the Admin UI.

---

## API Reference

### `GET /health`

Liveness check.

```json
{ "status": "ok", "version": "0.1.0", "port": 9000 }
```

### `POST /search`

Search log files for lines matching given keywords.

**Request**
```json
{
  "keywords": ["curve", "building", "complete"],
  "log_paths": ["/opt/app/logs/*.log", "/var/log/curve-builder.log"],
  "time_window_minutes": 60,
  "max_lines": 50
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `keywords` | `string[]` | yes | — | Case-insensitive. A line matches if it contains **any** keyword. |
| `log_paths` | `string[]` | yes | — | File paths or glob patterns, expanded at search time. |
| `time_window_minutes` | `integer` | no | none | Only return lines within the last N minutes. Lines with unparseable timestamps are always included. |
| `max_lines` | `integer` | no | `50` | Max matched lines per file (counts remain accurate). |

**Response**
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
  "total_files_searched": 2
}
```

---

## Timestamp parsing

When `time_window_minutes` is set, the sidecar parses timestamps from the start of each line. Supported formats:

| Format | Example |
|--------|---------|
| RFC 3339 / ISO 8601 | `2024-01-15T14:23:01Z` |
| `YYYY-MM-DD HH:MM:SS` | `2024-01-15 14:23:01` |

Lines with unparseable timestamps are **always included** (fail-open).

---

## Source layout

```
sidecar/src/
├── main.rs          ← tokio runtime, axum router, startup logging
├── config.rs        ← TOML + env + CLI layered config (clap derive)
├── api.rs           ← /health and /search axum handlers
├── search.rs        ← glob expansion, file reading, keyword matching, time filtering
└── registration.rs  ← self-registration POST + 30s heartbeat loop
```

---

## Deployment

### systemd (Linux)

See [`../deploy/logsight-sidecar.service`](../deploy/logsight-sidecar.service).

```bash
sudo cp target/release/logsight-sidecar /usr/local/bin/
sudo useradd -r -s /bin/false logsight
sudo cp ../deploy/logsight-sidecar.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now logsight-sidecar
```

### Docker

```dockerfile
FROM scratch
COPY target/x86_64-unknown-linux-musl/release/logsight-sidecar /logsight-sidecar
EXPOSE 9000
ENTRYPOINT ["/logsight-sidecar"]
```

---

## Running tests

```bash
cd sidecar
cargo test
```
