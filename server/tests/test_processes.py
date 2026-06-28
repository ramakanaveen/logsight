"""Tests for ProcessDefinition CRUD — no machine/port fields in Phase 2."""
import uuid
import pytest

pytestmark = pytest.mark.anyio


async def test_list_processes_empty(client):
    resp = await client.get("/v1/processes")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_process(client, sample_process_payload):
    resp = await client.post("/v1/processes", json=sample_process_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "CurveBuilder"
    assert data["description"] == "Builds yield curves each morning"
    assert len(data["example_qa"]) == 1
    assert "id" in data
    # Phase 2: no machine_host / sidecar_port / log_paths on ProcessDefinition
    assert "machine_host" not in data
    assert "sidecar_port" not in data
    assert "log_paths" not in data


async def test_create_process_minimal(client):
    resp = await client.post("/v1/processes", json={"name": "RiskEngine"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "RiskEngine"
    assert data["description"] == ""
    assert data["example_qa"] == []


async def test_list_processes_returns_created(client, created_process):
    resp = await client.get("/v1/processes")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == created_process["id"]


async def test_update_process_description(client, created_process):
    pid = created_process["id"]
    resp = await client.put(f"/v1/processes/{pid}", json={"description": "Updated desc"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated desc"
    assert resp.json()["name"] == "CurveBuilder"


async def test_update_process_not_found(client):
    resp = await client.put(f"/v1/processes/{uuid.uuid4()}", json={"description": "x"})
    assert resp.status_code == 404


async def test_delete_process(client, created_process):
    pid = created_process["id"]
    resp = await client.delete(f"/v1/processes/{pid}")
    assert resp.status_code == 204
    assert (await client.get("/v1/processes")).json() == []


async def test_delete_process_not_found(client):
    resp = await client.delete(f"/v1/processes/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_update_example_qa(client, created_process):
    pid = created_process["id"]
    new_qa = [{"question": "Is it running?", "answer": "Look for started"}]
    resp = await client.put(f"/v1/processes/{pid}", json={"example_qa": new_qa})
    assert resp.status_code == 200
    assert resp.json()["example_qa"] == new_qa
