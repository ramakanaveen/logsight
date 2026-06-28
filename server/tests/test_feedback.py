"""Unit tests for feedback CRUD endpoints."""
import uuid
import pytest

pytestmark = pytest.mark.anyio


async def _create_conversation_and_message(client, mock_agent) -> tuple[str, str]:
    """Helper: chat once to get a conv_id + message_id."""
    import json as json_mod
    resp = await client.post("/v1/chat/stream", json={"question": "Test"})
    assert resp.status_code == 200
    events = []
    for line in resp.content.decode().splitlines():
        if line.startswith("data: "):
            try:
                events.append(json_mod.loads(line[6:]))
            except Exception:
                pass
    done = next(e for e in events if e["type"] == "done")
    return done["data"]["conversation_id"], done["data"]["message_id"]


async def test_submit_thumbs_up(client, mock_agent):
    conv_id, msg_id = await _create_conversation_and_message(client, mock_agent)
    resp = await client.post(
        "/v1/feedback",
        json={"conversation_id": conv_id, "message_id": msg_id, "rating": 1, "comment": ""},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["rating"] == 1
    assert data["conversation_id"] == conv_id


async def test_submit_thumbs_down_with_comment(client, mock_agent):
    conv_id, msg_id = await _create_conversation_and_message(client, mock_agent)
    resp = await client.post(
        "/v1/feedback",
        json={
            "conversation_id": conv_id,
            "message_id": msg_id,
            "rating": -1,
            "comment": "Missing context",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["rating"] == -1
    assert data["comment"] == "Missing context"


async def test_list_feedback_empty(client):
    resp = await client.get("/v1/feedback")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_feedback_after_submit(client, mock_agent):
    conv_id, msg_id = await _create_conversation_and_message(client, mock_agent)
    await client.post(
        "/v1/feedback",
        json={"conversation_id": conv_id, "message_id": msg_id, "rating": 1, "comment": ""},
    )
    resp = await client.get("/v1/feedback")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_feedback_invalid_rating(client):
    resp = await client.post(
        "/v1/feedback",
        json={
            "conversation_id": str(uuid.uuid4()),
            "message_id": str(uuid.uuid4()),
            "rating": 0,
            "comment": "",
        },
    )
    assert resp.status_code == 422


async def test_feedback_nonexistent_conversation(client):
    resp = await client.post(
        "/v1/feedback",
        json={
            "conversation_id": str(uuid.uuid4()),
            "message_id": str(uuid.uuid4()),
            "rating": 1,
            "comment": "",
        },
    )
    assert resp.status_code == 404
