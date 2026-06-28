"""Tests for topology API: namespaces, machines, sidecar registration, machine-process assignments."""
import uuid
import pytest

pytestmark = pytest.mark.anyio


# ── Namespace CRUD ────────────────────────────────────────────────────────────

async def test_create_namespace(client):
    resp = await client.post("/v1/namespaces", json={"name": "STIRT", "description": "FX"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "STIRT"
    assert data["description"] == "FX"
    assert "id" in data


async def test_list_namespaces_empty(client):
    resp = await client.get("/v1/namespaces")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_namespaces_returns_created(client, namespace):
    resp = await client.get("/v1/namespaces")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "STIRT"


async def test_update_namespace(client, namespace):
    resp = await client.put(f"/v1/namespaces/{namespace['id']}", json={"description": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated"
    assert resp.json()["name"] == "STIRT"


async def test_delete_namespace(client, namespace):
    resp = await client.delete(f"/v1/namespaces/{namespace['id']}")
    assert resp.status_code == 204
    assert (await client.get("/v1/namespaces")).json() == []


async def test_delete_namespace_not_found(client):
    resp = await client.delete(f"/v1/namespaces/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Machine CRUD ──────────────────────────────────────────────────────────────

async def test_create_machine(client, namespace):
    ns_id = namespace["id"]
    resp = await client.post(
        f"/v1/namespaces/{ns_id}/machines",
        json={"hostname": "server1.stirt.internal"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["hostname"] == "server1.stirt.internal"
    assert data["namespace_id"] == ns_id


async def test_create_machine_namespace_not_found(client):
    resp = await client.post(
        f"/v1/namespaces/{uuid.uuid4()}/machines",
        json={"hostname": "server1"},
    )
    assert resp.status_code == 404


async def test_list_machines(client, namespace, machine):
    ns_id = namespace["id"]
    resp = await client.get(f"/v1/namespaces/{ns_id}/machines")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["hostname"] == "server1.stirt.internal"


async def test_update_machine(client, machine):
    resp = await client.put(f"/v1/machines/{machine['id']}", json={"description": "Primary"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "Primary"


async def test_delete_machine(client, namespace, machine):
    resp = await client.delete(f"/v1/machines/{machine['id']}")
    assert resp.status_code == 204
    ns_id = namespace["id"]
    assert (await client.get(f"/v1/namespaces/{ns_id}/machines")).json() == []


# ── Sidecar registration ──────────────────────────────────────────────────────

async def test_register_sidecar(client, machine):
    resp = await client.post(
        "/v1/sidecars/register",
        json={"machine_host": "server1.stirt.internal", "port": 9000},
    )
    assert resp.status_code == 201
    assert "sidecar_id" in resp.json()


async def test_register_sidecar_unknown_machine(client):
    resp = await client.post(
        "/v1/sidecars/register",
        json={"machine_host": "unknown.host", "port": 9000},
    )
    assert resp.status_code == 404


async def test_register_sidecar_upserts(client, machine, sidecar):
    sidecar_id = sidecar["sidecar_id"]
    # Re-register same machine — should update existing row, return same or new id
    resp = await client.post(
        "/v1/sidecars/register",
        json={"machine_host": "server1.stirt.internal", "port": 9001},
    )
    assert resp.status_code == 201
    # Only one sidecar per machine
    resp2 = await client.get("/v1/sidecars")
    assert len(resp2.json()) == 1
    assert resp2.json()[0]["port"] == 9001


async def test_heartbeat_sidecar(client, machine, sidecar):
    sidecar_id = sidecar["sidecar_id"]
    resp = await client.post(f"/v1/sidecars/{sidecar_id}/heartbeat")
    assert resp.status_code == 204


async def test_deregister_sidecar(client, machine, sidecar):
    sidecar_id = sidecar["sidecar_id"]
    resp = await client.post(f"/v1/sidecars/{sidecar_id}/deregister")
    assert resp.status_code == 204
    sidecars = (await client.get("/v1/sidecars?status=dead")).json()
    assert any(s["id"] == sidecar_id for s in sidecars)


async def test_heartbeat_not_found(client):
    resp = await client.post(f"/v1/sidecars/{uuid.uuid4()}/heartbeat")
    assert resp.status_code == 404


# ── Machine-process assignment ────────────────────────────────────────────────

async def test_assign_process_to_machine(client, machine, created_process):
    machine_id = machine["id"]
    process_id = created_process["id"]
    resp = await client.post(
        f"/v1/machines/{machine_id}/processes",
        json={"process_definition_id": process_id, "log_paths": ["/opt/curve/logs/*.log"]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["process_name"] == "CurveBuilder"
    assert data["log_paths"] == ["/opt/curve/logs/*.log"]


async def test_assign_process_machine_not_found(client, created_process):
    resp = await client.post(
        f"/v1/machines/{uuid.uuid4()}/processes",
        json={"process_definition_id": created_process["id"], "log_paths": ["/x.log"]},
    )
    assert resp.status_code == 404


async def test_assign_process_definition_not_found(client, machine):
    resp = await client.post(
        f"/v1/machines/{machine['id']}/processes",
        json={"process_definition_id": str(uuid.uuid4()), "log_paths": ["/x.log"]},
    )
    assert resp.status_code == 404


async def test_list_machine_processes(client, machine_process, machine):
    resp = await client.get(f"/v1/machines/{machine['id']}/processes")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["process_name"] == "CurveBuilder"


async def test_remove_process_from_machine(client, machine_process, machine):
    mp_id = machine_process["id"]
    machine_id = machine["id"]
    resp = await client.delete(f"/v1/machines/{machine_id}/processes/{mp_id}")
    assert resp.status_code == 204
    assert (await client.get(f"/v1/machines/{machine_id}/processes")).json() == []


# ── Topology view ─────────────────────────────────────────────────────────────

async def test_topology_empty(client):
    resp = await client.get("/v1/topology")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_topology_returns_tree(client, namespace, machine, sidecar, machine_process):
    resp = await client.get("/v1/topology")
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 1
    assert tree[0]["namespace"]["name"] == "STIRT"
    machines = tree[0]["machines"]
    assert len(machines) == 1
    m = machines[0]
    assert m["machine"]["hostname"] == "server1.stirt.internal"
    assert m["sidecar"]["status"] == "alive"
    assert len(m["processes"]) == 1
    assert m["processes"][0]["name"] == "CurveBuilder"


async def test_topology_no_sidecar_shows_null(client, namespace, machine, machine_process):
    resp = await client.get("/v1/topology")
    assert resp.status_code == 200
    m = resp.json()[0]["machines"][0]
    assert m["sidecar"] is None
    assert len(m["processes"]) == 1
