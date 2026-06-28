"""Tests for the chat endpoints (non-streaming POST /v1/chat)."""
import json
import pytest
from unittest.mock import patch

pytestmark = pytest.mark.anyio


async def test_chat_empty_question_rejected(client):
    resp = await client.post("/v1/chat", json={"question": ""})
    assert resp.status_code == 422


async def test_chat_missing_question_rejected(client):
    resp = await client.post("/v1/chat", json={})
    assert resp.status_code == 422


async def test_chat_no_processes_returns_message(client):
    resp = await client.post("/v1/chat", json={"question": "Is curve building done?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "No processes" in data["answer"]
    assert "conversation_id" in data


async def test_chat_returns_answer_and_conversation_id(client, created_process, mock_agent):
    resp = await client.post("/v1/chat", json={"question": "Is curve building done?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Curve building" in data["answer"]
    assert "conversation_id" in data
    assert data["conversation_id"] is not None


async def test_chat_resumes_conversation(client, created_process, mock_agent):
    r1 = await client.post("/v1/chat", json={"question": "First question"})
    assert r1.status_code == 200
    conv_id = r1.json()["conversation_id"]

    r2 = await client.post("/v1/chat", json={"question": "Follow-up", "conversation_id": conv_id})
    assert r2.status_code == 200
    assert r2.json()["conversation_id"] == conv_id


async def test_chat_with_process_hint(client, created_process, mock_agent):
    resp = await client.post(
        "/v1/chat",
        json={"question": "Is it done?", "process_hint": "CurveBuilder"},
    )
    assert resp.status_code == 200
    assert resp.json()["answer"] is not None


async def test_chat_stream_returns_sse(client, created_process, mock_agent):
    resp = await client.post(
        "/v1/chat/stream",
        json={"question": "Is curve building done?"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "data:" in body
    assert '"type"' in body


async def test_chat_agent_exception_returns_error_event(client, created_process):
    async def _explode(**kwargs):
        raise RuntimeError("unexpected failure")

    with patch("app.routes.chat.run_agent", side_effect=_explode):
        resp = await client.post(
            "/v1/chat/stream", json={"question": "boom"}
        )
    assert resp.status_code == 200
    assert "error" in resp.text


async def test_chat_stream_persists_chart_and_sources_in_metadata(client, created_process):
    """Chart spec and sources emitted during streaming are saved to message metadata."""
    chart_spec = {
        "chart_type": "bar",
        "title": "Errors by Hour",
        "labels": ["09:00", "10:00"],
        "datasets": [{"label": "errors", "data": [3, 7]}],
    }

    async def _fake_with_chart(*, question, process_hint, history, process_definitions, db, emit):
        await emit("answer", {"text": "Here is a chart of errors."})
        await emit("chart", chart_spec)
        await emit("usage", {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15, "cost_usd": 0.0001})
        return (
            "Here is a chart of errors.",
            [],
            [
                {
                    "process_name": "CurveBuilder",
                    "machine_host": "srv1",
                    "files_searched": 1,
                    "lines_matched": 2,
                    "matched_files": ["/opt/logs/curve.log"],
                }
            ],
        )

    with patch("app.routes.chat.run_agent", side_effect=_fake_with_chart):
        resp = await client.post("/v1/chat/stream", json={"question": "Show chart"})
    assert resp.status_code == 200

    # Extract conversation_id from the 'done' SSE event
    conv_id = None
    for line in resp.text.splitlines():
        if line.startswith("data:"):
            evt = json.loads(line[5:])
            if evt["type"] == "done":
                conv_id = evt["data"]["conversation_id"]
    assert conv_id is not None, "Expected a 'done' event with conversation_id"

    # Fetch messages and verify metadata was persisted
    msgs_resp = await client.get(f"/v1/conversations/{conv_id}/messages")
    assert msgs_resp.status_code == 200
    msgs = msgs_resp.json()
    asst = next((m for m in msgs if m["role"] == "assistant"), None)
    assert asst is not None

    metadata = asst.get("metadata") or {}
    assert metadata.get("chart") == chart_spec, "Chart spec not persisted in metadata"
    assert len(metadata.get("sources", [])) == 1
    assert metadata["sources"][0]["process"] == "CurveBuilder"
    assert metadata["sources"][0]["machine"] == "srv1"
    assert "/opt/logs/curve.log" in metadata["sources"][0]["matched_files"]
    assert metadata.get("usage", {}).get("total_tokens") == 15
