# LogSight Architecture

## System Overview

LogSight is a distributed log intelligence system. Traders ask questions in plain English; an LLM agent fans out searches to lightweight Rust sidecars on each machine and returns a summarised answer.

```mermaid
graph TB
    subgraph UI["React UI  :5173"]
        Chat["/chat — Trader chat"]
        Admin["/admin — Fleet management"]
    end

    subgraph Server["Python FastAPI Server  :8080"]
        Agent["Agentic Loop\n(Claude tool-use + extended thinking)"]
        Routes["REST + SSE Routes\n/v1/chat/stream · /v1/topology · /v1/feedback"]
        DB["PostgreSQL\nconversations · messages · processes\nnamespaces · machines · sidecars · feedback"]
    end

    subgraph Fleet["Production Machines"]
        SC1["Sidecar\nserver1:9000"]
        SC2["Sidecar\nserver2:9000"]
        SC3["Sidecar\nserver3:9000"]
        L1["/opt/app/logs/*.log"]
        L2["/var/log/curve-builder.log"]
        L3["/opt/risk/logs/*.log"]
    end

    Chat -->|"POST /v1/chat/stream\ntext/event-stream"| Routes
    Admin -->|"CRUD /v1/topology\n/v1/processes"| Routes
    Routes --> Agent
    Agent -->|"parallel httpx"| SC1
    Agent -->|"parallel httpx"| SC2
    Agent -->|"parallel httpx"| SC3
    Routes <--> DB
    SC1 --> L1
    SC2 --> L2
    SC3 --> L3
    SC1 -.->|"POST /v1/topology/register\nheartbeat every 30s"| Routes
    SC2 -.->|"heartbeat"| Routes
    SC3 -.->|"heartbeat"| Routes
```

---

## Fleet Topology Data Model

```mermaid
erDiagram
    NAMESPACE ||--o{ MACHINE : contains
    MACHINE ||--o| SIDECAR_INSTANCE : "has (optional)"
    MACHINE ||--o{ MACHINE_PROCESS : "runs"
    PROCESS_DEFINITION ||--o{ MACHINE_PROCESS : "defines"
    CONVERSATION ||--o{ MESSAGE : contains
    MESSAGE ||--o{ FEEDBACK : receives

    NAMESPACE {
        uuid id PK
        text name
        text description
        timestamp created_at
    }
    MACHINE {
        uuid id PK
        uuid namespace_id FK
        text hostname
        text description
    }
    SIDECAR_INSTANCE {
        uuid id PK
        uuid machine_id FK
        int port
        text status
        timestamp last_heartbeat
        timestamp registered_at
    }
    PROCESS_DEFINITION {
        uuid id PK
        text name
        text description
        jsonb example_qa
    }
    MACHINE_PROCESS {
        uuid id PK
        uuid machine_id FK
        uuid process_definition_id FK
        text[] log_paths
    }
    CONVERSATION {
        uuid id PK
        timestamp created_at
    }
    MESSAGE {
        uuid id PK
        uuid conversation_id FK
        text role
        text content
        jsonb metadata_
        timestamp created_at
    }
    FEEDBACK {
        uuid id PK
        uuid conversation_id FK
        uuid message_id FK
        int rating
        text comment
        timestamp created_at
    }
```

---

## Agentic Loop — Query Flow

```mermaid
sequenceDiagram
    participant T as Trader
    participant UI as React UI
    participant S as FastAPI Server
    participant C as Claude API
    participant SC as Sidecar(s)

    T->>UI: "Is curve building complete for today?"
    UI->>S: POST /v1/chat/stream (SSE)
    S->>S: Load conversation history
    S->>C: messages.create(tools=[list_sidecars, search_logs, render_chart, ask_user])

    loop Agentic loop (tool-use)
        C-->>S: SSE: thinking block
        S-->>UI: event: thinking
        C-->>S: tool_use: list_sidecars(process_name="CurveBuilder")
        S-->>UI: event: tool_call
        S->>S: Query DB → alive sidecars with CurveBuilder
        S->>C: tool_result: [{sidecar_id, machine_host, port}]
        C-->>S: tool_use: search_logs(sidecar_id, keywords=["curve","complete","building"])
        S->>SC: POST /search {keywords, log_paths, time_window_minutes}
        SC-->>S: {results: [{path, matched_lines, total_matched}]}
        S->>C: tool_result: raw log lines
    end

    C-->>S: end_turn: final answer text (markdown)
    S-->>UI: event: answer
    S-->>UI: event: sources [{process, machine, matched_files}]
    S-->>UI: event: usage {input_tokens, output_tokens, cost_usd}
    S-->>UI: event: done {conversation_id, message_id}
    S->>S: Persist conversation + messages
    UI->>T: Rendered markdown answer + source chips
```

---

## SSE Event Stream

When a trader sends a question, the server responds with a `text/event-stream`. Each line is a JSON object:

```mermaid
stateDiagram-v2
    [*] --> thinking : Claude begins reasoning
    thinking --> tool_call : Claude calls a tool
    tool_call --> tool_result : Server executes tool
    tool_result --> thinking : Claude continues
    thinking --> clarify : Agent needs user input
    clarify --> [*] : done{clarify=true}
    thinking --> answer : Claude produces answer
    tool_call --> chart : render_chart called
    answer --> sources : Source attribution
    sources --> usage : Token/cost metrics
    usage --> done : Stream complete
    done --> [*]
```

---

## Sidecar Self-Registration

```mermaid
sequenceDiagram
    participant SC as Sidecar (startup)
    participant S as Server

    SC->>S: POST /v1/sidecars/register {machine_host, port, version}
    S->>S: Lookup Machine by hostname
    alt Machine found
        S-->>SC: 201 {sidecar_id}
        SC->>SC: Store sidecar_id
        loop Every 30s
            SC->>S: POST /v1/sidecars/{id}/heartbeat
            S->>S: Update last_heartbeat, status=alive
        end
    else Machine not found
        S-->>SC: 404 — pre-register machine in Admin UI first
    end

    Note over S: Background task every 30s:<br/>mark sidecars dead if heartbeat > 60s ago
```
