"""Tests for conversation history API."""
import pytest

pytestmark = pytest.mark.anyio


async def test_list_conversations_empty(client):
    resp = await client.get("/v1/conversations")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_chat_creates_conversation(client, created_process, mock_agent):
    r = await client.post("/v1/chat", json={"question": "Is curve done?"})
    assert r.status_code == 200
    conv_id = r.json()["conversation_id"]

    convs = (await client.get("/v1/conversations")).json()
    assert len(convs) == 1
    assert convs[0]["id"] == conv_id


async def test_get_messages_for_conversation(client, created_process, mock_agent):
    r = await client.post("/v1/chat", json={"question": "Is curve done?"})
    conv_id = r.json()["conversation_id"]

    msgs = (await client.get(f"/v1/conversations/{conv_id}/messages")).json()
    assert len(msgs) == 2  # user + assistant
    roles = [m["role"] for m in msgs]
    assert "user" in roles
    assert "assistant" in roles


async def test_multi_turn_conversation(client, created_process, mock_agent):
    r1 = await client.post("/v1/chat", json={"question": "First question"})
    conv_id = r1.json()["conversation_id"]

    r2 = await client.post("/v1/chat", json={"question": "Second question", "conversation_id": conv_id})
    assert r2.json()["conversation_id"] == conv_id

    msgs = (await client.get(f"/v1/conversations/{conv_id}/messages")).json()
    assert len(msgs) == 4  # 2 turns × (user + assistant)


async def test_delete_conversation(client, created_process, mock_agent):
    r = await client.post("/v1/chat", json={"question": "Test"})
    conv_id = r.json()["conversation_id"]

    del_resp = await client.delete(f"/v1/conversations/{conv_id}")
    assert del_resp.status_code == 204

    assert (await client.get("/v1/conversations")).json() == []


async def test_delete_conversation_not_found(client):
    import uuid
    resp = await client.delete(f"/v1/conversations/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_get_messages_conversation_not_found(client):
    import uuid
    resp = await client.get(f"/v1/conversations/{uuid.uuid4()}/messages")
    assert resp.status_code == 404
