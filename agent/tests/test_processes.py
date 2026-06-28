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
    assert data["machine_host"] == "server1.prod"
    assert data["sidecar_port"] == 9000
    assert data["log_paths"] == ["/opt/app/logs/curve.log"]
    assert len(data["example_qa"]) == 1
    assert "id" in data


async def test_create_process_default_port(client, sample_process_payload):
    payload = {**sample_process_payload}
    del payload["sidecar_port"]
    resp = await client.post("/v1/processes", json=payload)
    assert resp.status_code == 201
    assert resp.json()["sidecar_port"] == 9000


async def test_list_processes_returns_created(client, created_process):
    resp = await client.get("/v1/processes")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == created_process["id"]


async def test_update_process(client, created_process):
    process_id = created_process["id"]
    resp = await client.put(f"/v1/processes/{process_id}", json={"sidecar_port": 9001})
    assert resp.status_code == 200
    assert resp.json()["sidecar_port"] == 9001
    assert resp.json()["name"] == "CurveBuilder"  # other fields unchanged


async def test_update_process_not_found(client):
    import uuid
    resp = await client.put(f"/v1/processes/{uuid.uuid4()}", json={"sidecar_port": 9001})
    assert resp.status_code == 404


async def test_delete_process(client, created_process):
    process_id = created_process["id"]
    resp = await client.delete(f"/v1/processes/{process_id}")
    assert resp.status_code == 204

    resp = await client.get("/v1/processes")
    assert resp.json() == []


async def test_delete_process_not_found(client):
    import uuid
    resp = await client.delete(f"/v1/processes/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_update_log_paths(client, created_process):
    process_id = created_process["id"]
    new_paths = ["/new/path/*.log", "/another/*.log"]
    resp = await client.put(f"/v1/processes/{process_id}", json={"log_paths": new_paths})
    assert resp.status_code == 200
    assert resp.json()["log_paths"] == new_paths


async def test_update_example_qa(client, created_process):
    process_id = created_process["id"]
    new_qa = [{"question": "Is it running?", "answer": "Look for started"}]
    resp = await client.put(f"/v1/processes/{process_id}", json={"example_qa": new_qa})
    assert resp.status_code == 200
    assert resp.json()["example_qa"] == new_qa
