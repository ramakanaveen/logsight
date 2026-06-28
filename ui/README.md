# LogSight UI

React + TypeScript + Vite frontend for LogSight. Two routes: `/chat` for operators and `/admin` for fleet management.

---

## Quick start

```bash
cd ui
npm install
npm run dev     # starts at :5173, proxies /v1/* to :8080
```

Open:
- Chat: http://localhost:5173/chat
- Admin panel: http://localhost:5173/admin

Requires the LogSight server running on port 8080.

---

## Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/chat` | `ChatPage` | SSE streaming chat with conversation sidebar |
| `/admin` | `AdminPage` | Fleet topology viewer + process definition manager |
| `/` | — | Redirects to `/chat` |

---

## Component overview

```
src/
├── pages/
│   ├── ChatPage.tsx           ← conversation list sidebar + message thread
│   └── AdminPage.tsx          ← namespace/machine topology + process definitions
│
├── components/
│   ├── MessageBubble.tsx      ← single turn: thinking accordion, answer (markdown),
│   │                             sources, usage pill, download button, feedback buttons
│   ├── SourceChips.tsx        ← per-sidecar source chips; expands to show matched files
│   ├── ThinkingBlock.tsx      ← collapsible extended thinking text
│   ├── ToolCallTrace.tsx      ← collapsible tool call + result details
│   ├── ClarifyPrompt.tsx      ← ask_user prompt: free-text or option buttons
│   ├── CommandInput.tsx       ← textarea with /process autocomplete
│   ├── ConversationSidebar.tsx← conversation list with export button
│   ├── TopologyView.tsx       ← namespace → machine → sidecar tree
│   ├── ProcessDefinitions.tsx ← process definition table + add/edit modal
│   └── ChartBlock.tsx         ← recharts bar/line/pie from render_chart tool
│
├── hooks/
│   └── useChat.ts             ← sendMessage + SSE stream parsing → Zustand store
│
├── store.ts                   ← Zustand: turns[], conversationId, conversations[]
├── api.ts                     ← streamChat() async generator + REST helpers
└── types.ts                   ← ChatTurn, SSEEvent, SourceInfo, ProcessDefinition, etc.
```

---

## State management

Zustand store (`store.ts`) holds:

```typescript
{
  turns: ChatTurn[]           // current thread
  conversationId: string | null
  conversations: ConversationSummary[]
}
```

`useChat` hook wraps `sendMessage()` — it calls `streamChat()` (async generator over SSE), dispatches each event to the store, and never holds the whole store reference (uses per-field selectors to avoid re-render loops).

---

## SSE event handling

`streamChat()` in `api.ts` is an async generator. Each `data:` line is parsed and yielded as a typed `SSEEvent`. `useChat` switches on `event.type`:

| Event | Store action |
|-------|-------------|
| `thinking` | `updateTurn(idx, { thinkingText })` |
| `tool_call` | `appendToolCall(idx, tool, input)` |
| `tool_result` | `resolveToolCall(idx, tool, result)` |
| `answer` | `updateTurn(idx, { answerText })` |
| `sources` | `updateTurn(idx, { sources })` |
| `usage` | `updateTurn(idx, { usage })` |
| `chart` | `updateTurn(idx, { chart })` |
| `clarify` | `updateTurn(idx, { clarifyQuestion, clarifyOptions })` |
| `done` | `setConversationId(id)`, `updateTurn(idx, { loading: false })` |
| `error` | `updateTurn(idx, { error, loading: false })` |

---

## Running tests

```bash
cd ui
npm test               # run all Vitest tests in watch mode
npm run test -- --run  # single pass (CI)
```

Tests live alongside components in `src/components/__tests__/` and `src/hooks/__tests__/`.

---

## Build

```bash
npm run build    # output in dist/
npm run preview  # preview production build at :4173
```

The built `dist/` is served as static files by the FastAPI server in production (`/ui` mount in `server/main.py`). The Vite dev proxy (`/v1/* → :8080`) is only used during development.

---

## Tech stack

| Tool | Purpose |
|------|---------|
| React 19 | UI framework |
| TypeScript | Type safety |
| Vite | Dev server + bundler |
| Tailwind CSS v4 | Styling |
| Zustand | Global state |
| React Router v7 | Client-side routing |
| Lucide React | Icons |
| react-markdown + remark-gfm | Markdown rendering in answers |
| Recharts | Bar / line / pie charts |
| Vitest + Testing Library | Unit tests |
