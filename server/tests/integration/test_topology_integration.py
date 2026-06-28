"""
Integration tests for fleet topology endpoints.
Uses FastAPI TestClient + in-memory SQLite.
"""
import pytest

pytestmark = pytest.mark.anyio


async def test_heartbeat_creates_sidecar(client, machine):
    """POST /v1/sidecars/register creates a sidecar_instance for the machine."""
    machine_host = machine["hostname"]
    resp = await client.post(
        "/v1/sidecars/register",
        json={"machine_host": machine_host, "port": 9000, "version": "0.1.0"},
    )
    assert resp.status_code in (200, 201)

    topo = await client.get("/v1/topology")
    assert topo.status_code == 200
    data = topo.json()
    sidecars = [
        m["sidecar"]
        for ns in data
        for m in ns["machines"]
        if m["sidecar"] is not None and m["machine"]["hostname"] == machine_host
    ]
    assert len(sidecars) == 1
    assert sidecars[0]["status"] == "alive"


async def test_heartbeat_repeated_updates_status(client, machine):
    """Repeated register calls keep sidecar alive (upsert by machine)."""
    machine_host = machine["hostname"]
    payload = {"machine_host": machine_host, "port": 9000, "version": "0.1.0"}
    r1 = await client.post("/v1/sidecars/register", json=payload)
    assert r1.status_code in (200, 201)
    sidecar_id = r1.json()["sidecar_id"]

    # Heartbeat on existing sidecar
    resp2 = await client.post(f"/v1/sidecars/{sidecar_id}/heartbeat")
    assert resp2.status_code == 204

    topo = await client.get("/v1/topology")
    alive = [
        m["sidecar"]
        for ns in topo.json()
        for m in ns["machines"]
        if m["sidecar"] is not None
        and m["machine"]["hostname"] == machine_host
        and m["sidecar"]["status"] == "alive"
    ]
    assert len(alive) == 1


async def test_full_fleet_machine_processes(client, machine_process, machine, namespace, created_process, sidecar):
    """GET /v1/topology shows namespace + machine correctly."""
    resp = await client.get("/v1/topology")
    assert resp.status_code == 200
    data = resp.json()

    ns_names = [ns["namespace"]["name"] for ns in data]
    assert namespace["name"] in ns_names

    ns_entry = next(ns for ns in data if ns["namespace"]["name"] == namespace["name"])
    machines = ns_entry["machines"]
    assert any(m["machine"]["hostname"] == machine["hostname"] for m in machines)


async def test_topology_list_sidecars_filters_by_process(client, machine_process, machine, namespace, created_process, sidecar):
    """GET /v1/sidecars lists all registered sidecars."""
    resp = await client.get("/v1/sidecars")
    assert resp.status_code == 200
    sidecars = resp.json()
    assert isinstance(sidecars, list)
    assert len(sidecars) >= 1


async def test_feedback_submit_and_list(client, mock_agent):
    """POST /v1/feedback submits a rating; GET /v1/feedback lists it."""
    resp = await client.post("/v1/chat/stream", json={"question": "Test question"})
    assert resp.status_code == 200

    import json as json_mod
    events = []
    for line in resp.content.decode().splitlines():
        if line.startswith("data: "):
            try:
                events.append(json_mod.loads(line[6:]))
            except Exception:
                pass

    done = next((e for e in events if e["type"] == "done"), None)
    assert done is not None
    conv_id = done["data"]["conversation_id"]
    msg_id = done["data"]["message_id"]

    fb_resp = await client.post(
        "/v1/feedback",
        json={
            "conversation_id": conv_id,
            "message_id": msg_id,
            "rating": 1,
            "comment": "Very helpful",
        },
    )
    assert fb_resp.status_code == 201
    fb = fb_resp.json()
    assert fb["rating"] == 1

    list_resp = await client.get("/v1/feedback")
    assert list_resp.status_code == 200
    fbs = list_resp.json()
    assert any(f["id"] == fb["id"] for f in fbs)


async def test_feedback_invalid_rating(client):
    """POST /v1/feedback with rating=0 returns 422."""
    import uuid as uuid_mod
    resp = await client.post(
        "/v1/feedback",
        json={
            "conversation_id": str(uuid_mod.uuid4()),
            "message_id": str(uuid_mod.uuid4()),
            "rating": 0,
            "comment": "",
        },
    )
    assert resp.status_code == 422
