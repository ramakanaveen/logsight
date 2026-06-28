import pytest
from unittest.mock import patch, AsyncMock, MagicMock


pytestmark = pytest.mark.anyio


async def test_chat_no_processes(client):
    resp = await client.post("/v1/chat", json={"question": "Is curve building done?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "No processes" in data["answer"]
    assert data["sources"] == []


async def test_chat_empty_question_rejected(client):
    resp = await client.post("/v1/chat", json={"question": ""})
    assert resp.status_code == 422


async def test_chat_missing_question_rejected(client):
    resp = await client.post("/v1/chat", json={})
    assert resp.status_code == 422


async def test_chat_llm_no_relevant_processes(client, created_process):
    """When LLM returns no relevant process IDs, chat responds gracefully."""
    with patch("app.routes.chat.llm.identify_processes", return_value={"relevant_process_ids": [], "keywords": []}):
        resp = await client.post("/v1/chat", json={"question": "unrelated question"})
    assert resp.status_code == 200
    assert "couldn't identify" in resp.json()["answer"]


async def test_chat_full_flow(client, created_process):
    """Happy path: LLM routes → fanout → LLM summarizes → response with sources."""
    process_id = created_process["id"]

    routing_result = {"relevant_process_ids": [process_id], "keywords": ["curve", "complete"]}
    fanout_result = [{
        "ok": True,
        "host": "server1.prod",
        "port": 9000,
        "process_name": "CurveBuilder",
        "data": {
            "total_files_searched": 1,
            "results": [{"path": "/opt/app/logs/curve.log", "matched_lines": [], "total_matched": 5, "error": None}],
        },
    }]
    summary = "Curve building completed at 14:23 on server1.prod."

    with (
        patch("app.routes.chat.llm.identify_processes", return_value=routing_result),
        patch("app.routes.chat.fanout.fanout_search", new=AsyncMock(return_value=fanout_result)),
        patch("app.routes.chat.llm.summarize_results", return_value=summary),
    ):
        resp = await client.post("/v1/chat", json={"question": "Is curve building done?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == summary
    assert len(data["sources"]) == 1
    assert data["sources"][0]["process"] == "CurveBuilder"
    assert data["sources"][0]["machine"] == "server1.prod"
    assert data["sources"][0]["files_searched"] == 1
    assert data["sources"][0]["lines_matched"] == 5


async def test_chat_unreachable_sidecar_still_returns_answer(client, created_process):
    """Unreachable sidecar → answer still generated, source shows 0 lines."""
    process_id = created_process["id"]

    routing_result = {"relevant_process_ids": [process_id], "keywords": ["error"]}
    fanout_result = [{
        "ok": False,
        "host": "server1.prod",
        "port": 9000,
        "process_name": "CurveBuilder",
        "error": "Timeout connecting to server1.prod:9000",
    }]

    with (
        patch("app.routes.chat.llm.identify_processes", return_value=routing_result),
        patch("app.routes.chat.fanout.fanout_search", new=AsyncMock(return_value=fanout_result)),
        patch("app.routes.chat.llm.summarize_results", return_value="server1 was unreachable."),
    ):
        resp = await client.post("/v1/chat", json={"question": "Any errors?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["sources"][0]["lines_matched"] == 0
    assert data["sources"][0]["files_searched"] == 0


async def test_chat_llm_routing_failure_returns_502(client, created_process):
    with patch("app.routes.chat.llm.identify_processes", side_effect=Exception("API down")):
        resp = await client.post("/v1/chat", json={"question": "Is curve done?"})
    assert resp.status_code == 502
    assert "LLM routing failed" in resp.json()["detail"]


async def test_chat_llm_summarize_failure_returns_502(client, created_process):
    process_id = created_process["id"]
    routing_result = {"relevant_process_ids": [process_id], "keywords": ["curve"]}
    fanout_result = [{"ok": True, "host": "server1.prod", "port": 9000,
                      "process_name": "CurveBuilder",
                      "data": {"total_files_searched": 0, "results": []}}]

    with (
        patch("app.routes.chat.llm.identify_processes", return_value=routing_result),
        patch("app.routes.chat.fanout.fanout_search", new=AsyncMock(return_value=fanout_result)),
        patch("app.routes.chat.llm.summarize_results", side_effect=Exception("API down")),
    ):
        resp = await client.post("/v1/chat", json={"question": "Is curve done?"})

    assert resp.status_code == 502
    assert "summarization failed" in resp.json()["detail"]
