"""Tests for the chat endpoints (non-streaming POST /v1/chat)."""
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
