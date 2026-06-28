# LogSight UIs

Two single-page HTML interfaces, served as static files by the agent at `/ui/chat/` and `/ui/admin/`. No build step, no framework — vanilla HTML/CSS/JS only.

---

## Trader Chat UI — `/ui/chat/`

**File:** `chat/index.html`

The primary interface for traders. Lets users ask plain-English questions and see answers with source attribution.

### Usage

1. Open `http://localhost:8080/ui/chat/` in a browser.
2. Type a question in the input box and press **Enter** or click **Ask**.
3. The UI shows a "Searching logs…" indicator while the request is in flight.
4. The answer appears as a chat bubble. Below it, source chips show which machines and processes contributed data.

### Source chips

Each chip shows:
```
server1.prod · CurveBuilder · 7 lines
```
- **Machine** (blue) — the hostname of the machine that was queried.
- **Process** — the registered process name.
- **lines** — total matching log lines found on that machine.

A chip with `0 lines` means the process was identified as relevant but no matching lines were found. An unreachable machine is noted in the answer text rather than a chip.

### Keyboard shortcut

`Enter` submits the question. `Shift+Enter` inserts a newline (for multi-line questions).

### What it calls

```
POST /v1/chat
Content-Type: application/json

{ "question": "..." }
```

Response fields used: `answer` (displayed as chat text), `sources` (rendered as chips).

---

## Admin UI — `/ui/admin/`

**File:** `admin/index.html`

Used by operators to register, update, and remove processes from the registry. Changes take effect immediately — the next chat request will use the updated registry.

### Process table

Lists all registered processes with columns:
- **Name** — display name
- **Machine** — hostname where the sidecar runs
- **Port** — sidecar port (default 9000)
- **Log Paths** — each path/glob shown as a tag
- **Description** — truncated to one line in the table

### Adding a process

Click **+ Add Process** to open the modal. Required fields:

| Field         | Notes                                                             |
|---------------|-------------------------------------------------------------------|
| Name          | Short identifier, e.g. `CurveBuilder`                            |
| Description   | Written for the LLM — be specific about what the process does and when. See guidance below. |
| Machine Host  | Hostname or IP of the machine running the sidecar, e.g. `server1.prod` |
| Sidecar Port  | Default `9000`; change if the sidecar was started on a different port |
| Log Paths     | One path or glob per line. These are forwarded to the sidecar's `/search` endpoint. |
| Example Q&A   | Optional but recommended. See guidance below.                     |

Click **Save** to create the process. The table refreshes automatically.

### Editing a process

Click **Edit** on any row to reopen the modal pre-filled with that process's current values. Click **Update** to save. All fields can be changed, including log paths and example Q&A.

### Deleting a process

Click **Delete** on any row. A browser confirmation dialog appears before the delete is sent. The process is removed from the registry immediately and will no longer be considered for future chat queries.

### Toast notifications

Success and error feedback appears as a small notification in the bottom-right corner and auto-dismisses after 3 seconds.

---

## Writing good process descriptions

The description is the most important field for routing accuracy. Claude reads it to decide whether a process is relevant to a given question.

**Too vague:**
> "Curve process"

**Better:**
> "Builds interest rate and credit yield curves each morning using Bloomberg market data. Runs on weekdays starting at 07:00 EST. Logs each curve individually and emits a 'Curve building completed' message when all curves are done."

Tips:
- Include **what** the process does, **when** it runs, and **what success/failure looks like** in the logs.
- Mention domain terms traders are likely to use (e.g. "SOFR curves", "risk engine", "EOD batch").

---

## Writing good example Q&A pairs

Example Q&A pairs give Claude concrete examples of how traders phrase questions about this process. They appear verbatim in the routing prompt.

**Without Q&A:**
Claude has to guess whether "Is the vol surface ready?" refers to the VolSurfaceBuilder process.

**With Q&A:**
```
Q: Is the vol surface ready?
A: Look for 'Vol surface generation complete' or 'all tenors done' in vol-surface-builder.log
```

Now Claude reliably routes that phrasing to the right process. Aim for 2–5 pairs per process, covering the most common question phrasings traders use.

---

## Static file serving

Both UIs are mounted by FastAPI as static file directories:

```python
app.mount("/ui/chat",  StaticFiles(directory="ui/chat",  html=True), name="chat-ui")
app.mount("/ui/admin", StaticFiles(directory="ui/admin", html=True), name="admin-ui")
```

The `html=True` flag causes FastAPI to serve `index.html` for directory requests, so `GET /ui/chat/` works without specifying the filename.

There are no build artifacts, node_modules, or bundlers. To modify a UI, edit the `.html` file directly and refresh the browser.
