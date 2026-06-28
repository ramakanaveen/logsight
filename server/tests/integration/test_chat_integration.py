"""
Integration tests for the chat SSE streaming endpoint.
Uses FastAPI TestClient + in-memory SQLite + mocked Anthropic client.
"""
import json
import uuid
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.agent import ClarifyPause

pytestmark = pytest.mark.anyio


def _parse_sse_events(body: bytes) -> list[dict]:
    events = []
    for line in body.decode().splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


async def test_chat_stream_returns_answer(client, mock_agent):
    """Full SSE stream: POST /v1/chat/stream emits answer + done events."""
    resp = await client.post("/v1/chat/stream", json={"question": "Is curve building done?"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse_events(resp.content)
    types = [e["type"] for e in events]

    assert "answer" in types
    assert "done" in types
    done = next(e for e in events if e["type"] == "done")
    assert "conversation_id" in done["data"]
    assert "message_id" in done["data"]


async def test_chat_stream_multi_turn(client, mock_agent):
    """Second POST with same conversation_id succeeds; history is loaded."""
    resp1 = await client.post("/v1/chat/stream", json={"question": "First question"})
    assert resp1.status_code == 200
    events1 = _parse_sse_events(resp1.content)
    done1 = next(e for e in events1 if e["type"] == "done")
    conv_id = done1["data"]["conversation_id"]

    resp2 = await client.post(
        "/v1/chat/stream",
        json={"question": "Follow-up question", "conversation_id": conv_id},
    )
    assert resp2.status_code == 200
    events2 = _parse_sse_events(resp2.content)
    assert any(e["type"] == "answer" for e in events2)
    done2 = next(e for e in events2 if e["type"] == "done")
    assert done2["data"]["conversation_id"] == conv_id


async def test_chat_stream_sources_in_response(client, mock_agent):
    """sources SSE event is present in the stream (may be empty list)."""
    resp = await client.post("/v1/chat/stream", json={"question": "Any errors?"})
    events = _parse_sse_events(resp.content)
    source_events = [e for e in events if e["type"] == "sources"]
    assert len(source_events) == 1
    assert isinstance(source_events[0]["data"], list)


async def test_chat_stream_clarify_pause(client):
    """When agent raises ClarifyPause, stream emits done with clarify=True."""
    async def _clarify_agent(*, question, process_hint, history, process_definitions, db, emit):
        await emit("clarify", {"question": "Which time range?", "options": []})
        raise ClarifyPause(question="Which time range?", messages=[])

    with patch("app.routes.chat.run_agent", side_effect=_clarify_agent):
        resp = await client.post("/v1/chat/stream", json={"question": "What happened?"})

    assert resp.status_code == 200
    events = _parse_sse_events(resp.content)
    clarify = [e for e in events if e["type"] == "clarify"]
    assert len(clarify) == 1
    done = next((e for e in events if e["type"] == "done"), None)
    assert done is not None
    assert done["data"].get("clarify") is True


async def test_chat_stream_usage_event(client, mock_agent):
    """usage SSE event is present with token counts."""
    resp = await client.post("/v1/chat/stream", json={"question": "Any question"})
    events = _parse_sse_events(resp.content)
    usage_events = [e for e in events if e["type"] == "usage"]
    assert len(usage_events) == 1
    u = usage_events[0]["data"]
    assert "input_tokens" in u
    assert "output_tokens" in u
    assert u["total_tokens"] == u["input_tokens"] + u["output_tokens"]


async def test_chat_nonstreaming_returns_answer(client, mock_agent):
    """Non-streaming POST /v1/chat returns answer and sources."""
    resp = await client.post("/v1/chat", json={"question": "Is curve building done?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert isinstance(data["sources"], list)
    assert "conversation_id" in data


async def test_chat_stream_error_handling(client):
    """If run_agent raises an unexpected exception, stream emits error event."""
    async def _bad_agent(**kwargs):
        raise RuntimeError("Unexpected failure")

    with patch("app.routes.chat.run_agent", side_effect=_bad_agent):
        resp = await client.post("/v1/chat/stream", json={"question": "Test"})

    events = _parse_sse_events(resp.content)
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert "Unexpected failure" in error_events[0]["data"]["message"]
