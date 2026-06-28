# LogSight API Reference

Base URL: `http://localhost:8080` (dev) · configured via `LOGSIGHT_HOST` / `LOGSIGHT_PORT`

---

## Chat

### `POST /v1/chat/stream` — Streaming chat (SSE)

Sends a question and receives a server-sent event stream.

**Request**
```json
{
  "question": "Is curve building complete for today?",
  "conversation_id": "uuid (optional — omit for new conversation)",
  "process_hint": "CurveBuilder (optional)"
}
```

**Response** — `Content-Type: text/event-stream`

Each line: `data: {"type": "<event>", "data": { ... }}\n\n`

| Event | Data shape | Description |
|-------|-----------|-------------|
| `thinking` | `{"text": "..."}` | Claude's extended thinking block |
| `tool_call` | `{"name": "search_logs", "input": {...}}` | Tool invoked by agent |
| `tool_result` | `{"result": {...}}` | Tool execution result |
| `clarify` | `{"question": "...", "options": ["A","B"]}` | Agent needs user input |
| `answer` | `{"text": "..."}` | Final markdown answer |
| `chart` | `{"chart_type": "bar", "title": "...", "labels": [...], "datasets": [...]}` | Chart to render |
| `sources` | `[{"process":"...","machine":"...","files_searched":1,"lines_matched":5,"matched_files":["..."]}]` | Log source attribution |
| `usage` | `{"input_tokens":1200,"output_tokens":300,"total_tokens":1500,"cost_usd":0.0081}` | Token usage + cost |
| `done` | `{"conversation_id":"uuid","message_id":"uuid"}` | Stream complete |
| `error` | `{"message": "..."}` | Unrecoverable error |

---

### `POST /v1/chat` — Non-streaming chat

**Request** — same as `/v1/chat/stream`

**Response**
```json
{
  "answer": "Curve building completed at 14:23 on server1.",
  "sources": [{ "process": "CurveBuilder", "machine": "server1", "lines_matched": 3 }],
  "conversation_id": "uuid"
}
```

---

## Conversations

### `GET /v1/conversations` — List conversations
```json
[{ "id": "uuid", "created_at": "2026-06-28T09:00:00" }]
```

### `GET /v1/conversations/{id}/messages` — Get messages
```json
[{ "id": "uuid", "role": "user|assistant", "content": "...", "created_at": "..." }]
```

### `DELETE /v1/conversations/{id}` — Delete conversation
`204 No Content`

---

## Process Definitions

### `GET /v1/processes`
```json
[{ "id": "uuid", "name": "CurveBuilder", "description": "...", "example_qa": [...] }]
```

### `POST /v1/processes` — Register process
**Request**
```json
{
  "name": "CurveBuilder",
  "description": "Builds yield curves each morning from market data",
  "example_qa": [{ "question": "Is curve done?", "answer": "Look for 'completed' in logs" }]
}
```
`201 Created`

### `PUT /v1/processes/{id}` — Update process
Same body as POST. `200 OK`

### `DELETE /v1/processes/{id}`
`204 No Content`

---

## Fleet Topology

### `GET /v1/topology` — Full fleet tree
```json
[
  {
    "namespace": { "id": "uuid", "name": "STIRT" },
    "machines": [
      {
        "machine": { "id": "uuid", "hostname": "server1.stirt.internal" },
        "sidecar": { "id": "uuid", "status": "alive", "port": 9000, "last_heartbeat": "..." },
        "processes": [{ "id": "uuid", "process_name": "CurveBuilder", "log_paths": [...] }]
      }
    ]
  }
]
```

### `POST /v1/namespaces` — Create namespace
```json
{ "name": "STIRT", "description": "Structured Interest Rate Trading" }
```

### `POST /v1/namespaces/{ns_id}/machines` — Add machine
```json
{ "hostname": "server1.stirt.internal", "description": "Primary curve builder host" }
```

### `POST /v1/machines/{machine_id}/processes` — Assign process to machine
```json
{
  "process_definition_id": "uuid",
  "log_paths": ["/opt/app/logs/*.log", "/var/log/curve-builder.log"]
}
```

### `POST /v1/sidecars/register` — Sidecar self-registration
```json
{ "machine_host": "server1.stirt.internal", "port": 9000, "version": "0.1.0" }
```
Response: `201 {"sidecar_id": "uuid"}`

### `POST /v1/sidecars/{sidecar_id}/heartbeat`
`204 No Content` — updates `last_heartbeat`, keeps status `alive`

### `GET /v1/sidecars` — List all sidecars
```json
[{ "id": "uuid", "machine_id": "uuid", "port": 9000, "status": "alive|dead", "last_heartbeat": "..." }]
```

---

## Feedback

### `POST /v1/feedback` — Submit rating
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "rating": 1,
  "comment": "Very helpful, found the issue immediately"
}
```
`rating`: `1` = thumbs up, `-1` = thumbs down

`201 Created`

### `GET /v1/feedback` — List all feedback (admin)
```json
[{ "id": "uuid", "rating": 1, "comment": "...", "created_at": "..." }]
```

---

## Health

### `GET /v1/health`
```json
{ "status": "ok", "version": "0.2.0" }
```

---

## Sidecar API

The sidecar runs on each machine (default port `9000`).

### `GET /health`
```json
{ "status": "ok", "version": "0.1.0", "port": 9000 }
```

### `POST /search`
**Request**
```json
{
  "keywords": ["curve", "building", "complete"],
  "log_paths": ["/opt/app/logs/*.log", "/var/log/curve-builder.log"],
  "time_window_minutes": 60,
  "max_lines": 50
}
```
**Response**
```json
{
  "results": [
    {
      "path": "/opt/app/logs/curve-builder.log",
      "matched_lines": [
        { "line_number": 1234, "content": "2026-06-28 14:23:01 INFO Curve building completed" }
      ],
      "total_matched": 1,
      "error": null
    }
  ],
  "total_files_searched": 2
}
```

---

## Agent Tools (internal)

These are the tools Claude can call inside the agentic loop. They are not directly callable via HTTP.

| Tool | Description |
|------|-------------|
| `list_sidecars(process_name?, machine_host?)` | Find alive sidecars, optionally filtered by process or hostname |
| `search_logs(sidecar_id, process_name, keywords, log_paths?, time_window_minutes?, max_lines?)` | Search log files on a specific sidecar |
| `render_chart(chart_type, title, labels, datasets)` | Emit a chart to the UI (bar/line/pie) |
| `ask_user(question, options?)` | Pause and ask the trader a clarifying question; optionally present buttons |
