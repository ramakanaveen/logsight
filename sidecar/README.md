# LogSight Sidecar

A lightweight, statically-linked Rust binary that runs on every machine you want to monitor. It exposes a small HTTP API over which the central agent can search log files on that machine.

---

## Overview

- **Read-only** — only reads files where it has filesystem permissions; never writes.
- **Zero dependencies** — single binary, no runtime libraries required.
- **Glob-aware** — log paths can include `*` and `**` patterns.
- **Time-windowed search** — can limit matches to logs written within the last N minutes.

---

## Building

Requires Rust 1.75+ (install via [rustup](https://rustup.rs)).

```bash
cd sidecar

# Debug build (faster, larger binary)
cargo build

# Release build (optimized, stripped)
cargo build --release

# Binary location
./target/release/logsight-sidecar
```

Cross-compile for Linux from macOS (requires `cross`):

```bash
cargo install cross
cross build --release --target x86_64-unknown-linux-musl
```

The `musl` target produces a fully static binary with no glibc dependency — ideal for deploying to any Linux machine.

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
log_dir = "/var/log"   # optional: adds this dir to search hints
# token = "secret"     # optional: auth token (Phase 2)
```

### Environment variables

| Variable           | Default | Description                   |
|--------------------|---------|-------------------------------|
| `LOGSIGHT_PORT`    | `9000`  | Port to listen on             |
| `LOGSIGHT_LOG_DIR` | —       | Default log directory hint    |
| `LOGSIGHT_TOKEN`   | —       | Auth token (Phase 2)          |

### CLI flags

```
logsight-sidecar [OPTIONS]

Options:
      --port <PORT>         Port to listen on [env: LOGSIGHT_PORT]
      --log-dir <LOG_DIR>   Default log directory [env: LOGSIGHT_LOG_DIR]
      --token <TOKEN>       Auth token [env: LOGSIGHT_TOKEN]
      --config <CONFIG>     Path to config file [default: logsight.toml]
  -h, --help                Print help
```

---

## Running

```bash
# Using defaults (port 9000, looks for logsight.toml in cwd)
./logsight-sidecar

# Override port and log dir
./logsight-sidecar --port 9001 --log-dir /opt/app/logs

# Using environment variables
LOGSIGHT_PORT=9001 ./logsight-sidecar
```

Set `RUST_LOG=logsight=debug` for verbose logging, `RUST_LOG=logsight=info` for normal operation.

---

## API Reference

### `GET /health`

Returns the sidecar's status. Used by the agent to verify a machine is reachable before querying.

**Response**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "port": 9000
}
```

**Example**

```bash
curl http://localhost:9000/health
```

---

### `POST /search`

Search log files on this machine for lines matching the given keywords.

**Request body**

```json
{
  "keywords": ["curve", "building", "complete"],
  "log_paths": ["/opt/app/logs/*.log", "/var/log/curve-builder.log"],
  "time_window_minutes": 60,
  "max_lines": 50
}
```

| Field                 | Type       | Required | Default | Description                                                       |
|-----------------------|------------|----------|---------|-------------------------------------------------------------------|
| `keywords`            | `string[]` | yes      | —       | Case-insensitive. A line matches if it contains **any** keyword.  |
| `log_paths`           | `string[]` | yes      | —       | File paths or glob patterns. Each is expanded at search time.     |
| `time_window_minutes` | `integer`  | no       | none    | Only return lines whose timestamp is within the last N minutes. Lines with no parseable timestamp are always included. |
| `max_lines`           | `integer`  | no       | `50`    | Max matched lines returned per file. Counts are still accurate.  |

**Response body**

```json
{
  "results": [
    {
      "path": "/opt/app/logs/curve-builder.log",
      "matched_lines": [
        { "line_number": 1234, "content": "2024-01-15 14:23:01 INFO Curve building completed" },
        { "line_number": 1301, "content": "2024-01-15 14:23:45 INFO Curve building complete for SOFR" }
      ],
      "total_matched": 5,
      "error": null
    },
    {
      "path": "/opt/app/logs/risk.log",
      "matched_lines": [],
      "total_matched": 0,
      "error": null
    }
  ],
  "total_files_searched": 2
}
```

| Field                          | Type      | Description                                                         |
|--------------------------------|-----------|---------------------------------------------------------------------|
| `results`                      | `array`   | One entry per resolved file (after glob expansion).                 |
| `results[].path`               | `string`  | Absolute path to the file that was searched.                        |
| `results[].matched_lines`      | `array`   | Up to `max_lines` matching lines.                                   |
| `results[].matched_lines[].line_number` | `integer` | 1-based line number in the file.                         |
| `results[].matched_lines[].content`     | `string`  | Full line text.                                          |
| `results[].total_matched`      | `integer` | Total lines that matched (may exceed `max_lines`).                  |
| `results[].error`              | `string?` | Non-null if this file could not be opened or the glob failed.       |
| `total_files_searched`         | `integer` | Total number of concrete files examined.                            |

**Error responses**

| Status | Condition                          |
|--------|------------------------------------|
| `400`  | `keywords` or `log_paths` is empty |
| `500`  | Unexpected internal error          |

**Example**

```bash
curl -s -X POST http://localhost:9000/search \
  -H 'Content-Type: application/json' \
  -d '{
    "keywords": ["error", "fatal"],
    "log_paths": ["/var/log/syslog"],
    "time_window_minutes": 30,
    "max_lines": 20
  }' | jq .
```

---

## Timestamp parsing

When `time_window_minutes` is set, the sidecar attempts to parse a timestamp from the **start of each line**. Supported formats:

| Format                  | Example                        |
|-------------------------|--------------------------------|
| RFC 3339 / ISO 8601     | `2024-01-15T14:23:01Z`         |
| `YYYY-MM-DD HH:MM:SS`   | `2024-01-15 14:23:01`          |

Lines whose timestamp cannot be parsed are **always included** (fail-open), so unstructured log entries are never silently dropped.

---

## Source layout

```
sidecar/src/
├── main.rs      — tokio runtime, axum router setup, startup logging
├── config.rs    — TOML + env + CLI layered config, clap derive
├── api.rs       — axum handler functions for /health and /search
└── search.rs    — glob expansion, file reading, keyword matching, time filtering
```

---

## Deployment

### systemd (Linux)

See [`../deploy/logsight-sidecar.service`](../deploy/logsight-sidecar.service).

```bash
# Copy binary
sudo cp target/release/logsight-sidecar /usr/local/bin/

# Create system user
sudo useradd -r -s /bin/false logsight

# Install service
sudo cp ../deploy/logsight-sidecar.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now logsight-sidecar

# Check status
sudo systemctl status logsight-sidecar
journalctl -u logsight-sidecar -f
```

The service file includes basic hardening: `NoNewPrivileges`, `ProtectSystem`, read-only bind mounts for log directories.

### Docker

```dockerfile
FROM scratch
COPY target/x86_64-unknown-linux-musl/release/logsight-sidecar /logsight-sidecar
EXPOSE 9000
ENTRYPOINT ["/logsight-sidecar"]
```

Or use the provided `docker-compose.yml` in `../deploy/`.

---

## Security notes

- The sidecar serves **all files it can read** to anyone who can reach its port. In Phase 1 there is no authentication. Restrict access at the network level (firewall, VPC security groups) so only the central agent host can reach port 9000.
- Auth token support is planned for Phase 2.
