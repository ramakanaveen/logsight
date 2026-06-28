"""Topology API: namespaces, machines, sidecar registration/heartbeat, machine-process assignments."""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Namespace, Machine, SidecarInstance, ProcessDefinition, MachineProcess
from app.schemas import (
    NamespaceCreate, NamespaceUpdate, NamespaceOut,
    MachineCreate, MachineUpdate, MachineOut,
    SidecarInstanceOut, SidecarRegisterRequest, SidecarRegisterResponse,
    SidecarHeartbeatRequest,
    MachineProcessCreate, MachineProcessOut,
    ProcessInTopology, MachineInTopology, NamespaceTopology,
)

router = APIRouter(tags=["topology"])


# ── Namespaces ────────────────────────────────────────────────────────────────

@router.get("/v1/namespaces", response_model=list[NamespaceOut])
async def list_namespaces(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Namespace).order_by(Namespace.name))
    return result.scalars().all()


@router.post("/v1/namespaces", response_model=NamespaceOut, status_code=201)
async def create_namespace(body: NamespaceCreate, db: AsyncSession = Depends(get_db)):
    ns = Namespace(id=uuid.uuid4(), name=body.name, description=body.description)
    db.add(ns)
    await db.commit()
    await db.refresh(ns)
    return ns


@router.put("/v1/namespaces/{ns_id}", response_model=NamespaceOut)
async def update_namespace(ns_id: uuid.UUID, body: NamespaceUpdate, db: AsyncSession = Depends(get_db)):
    ns = await db.get(Namespace, ns_id)
    if not ns:
        raise HTTPException(status_code=404, detail="Namespace not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(ns, field, value)
    await db.commit()
    await db.refresh(ns)
    return ns


@router.delete("/v1/namespaces/{ns_id}", status_code=204)
async def delete_namespace(ns_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ns = await db.get(Namespace, ns_id)
    if not ns:
        raise HTTPException(status_code=404, detail="Namespace not found")
    await db.delete(ns)
    await db.commit()


# ── Machines ──────────────────────────────────────────────────────────────────

@router.get("/v1/namespaces/{ns_id}/machines", response_model=list[MachineOut])
async def list_machines(ns_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Machine).where(Machine.namespace_id == ns_id).order_by(Machine.hostname)
    )
    return result.scalars().all()


@router.post("/v1/namespaces/{ns_id}/machines", response_model=MachineOut, status_code=201)
async def create_machine(ns_id: uuid.UUID, body: MachineCreate, db: AsyncSession = Depends(get_db)):
    ns = await db.get(Namespace, ns_id)
    if not ns:
        raise HTTPException(status_code=404, detail="Namespace not found")
    machine = Machine(id=uuid.uuid4(), namespace_id=ns_id, hostname=body.hostname, description=body.description)
    db.add(machine)
    await db.commit()
    await db.refresh(machine)
    return machine


@router.put("/v1/machines/{machine_id}", response_model=MachineOut)
async def update_machine(machine_id: uuid.UUID, body: MachineUpdate, db: AsyncSession = Depends(get_db)):
    machine = await db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(machine, field, value)
    await db.commit()
    await db.refresh(machine)
    return machine


@router.delete("/v1/machines/{machine_id}", status_code=204)
async def delete_machine(machine_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    machine = await db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    await db.delete(machine)
    await db.commit()


# ── Machine ↔ Process assignments ────────────────────────────────────────────

@router.get("/v1/machines/{machine_id}/processes", response_model=list[MachineProcessOut])
async def list_machine_processes(machine_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MachineProcess)
        .where(MachineProcess.machine_id == machine_id)
        .options(selectinload(MachineProcess.process_definition))
    )
    rows = result.scalars().all()
    return [
        MachineProcessOut(
            id=mp.id,
            machine_id=mp.machine_id,
            process_definition_id=mp.process_definition_id,
            process_name=mp.process_definition.name,
            log_paths=mp.log_paths,
        )
        for mp in rows
    ]


@router.post("/v1/machines/{machine_id}/processes", response_model=MachineProcessOut, status_code=201)
async def assign_process_to_machine(
    machine_id: uuid.UUID, body: MachineProcessCreate, db: AsyncSession = Depends(get_db)
):
    machine = await db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    pd = await db.get(ProcessDefinition, body.process_definition_id)
    if not pd:
        raise HTTPException(status_code=404, detail="ProcessDefinition not found")

    mp = MachineProcess(
        id=uuid.uuid4(),
        machine_id=machine_id,
        process_definition_id=body.process_definition_id,
        log_paths=body.log_paths,
    )
    db.add(mp)
    await db.commit()
    await db.refresh(mp)
    return MachineProcessOut(
        id=mp.id,
        machine_id=mp.machine_id,
        process_definition_id=mp.process_definition_id,
        process_name=pd.name,
        log_paths=mp.log_paths,
    )


@router.delete("/v1/machines/{machine_id}/processes/{mp_id}", status_code=204)
async def remove_process_from_machine(
    machine_id: uuid.UUID, mp_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    mp = await db.get(MachineProcess, mp_id)
    if not mp or mp.machine_id != machine_id:
        raise HTTPException(status_code=404, detail="MachineProcess not found")
    await db.delete(mp)
    await db.commit()


# ── Sidecar registration ──────────────────────────────────────────────────────

@router.post("/v1/sidecars/register", response_model=SidecarRegisterResponse, status_code=201)
async def register_sidecar(body: SidecarRegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Machine).where(Machine.hostname == body.machine_host)
    )
    machine = result.scalars().first()
    if not machine:
        raise HTTPException(
            status_code=404,
            detail=f"No machine registered with hostname {body.machine_host!r}. "
                   "Register the machine in the admin UI first.",
        )

    # Upsert: one sidecar per machine
    result = await db.execute(
        select(SidecarInstance).where(SidecarInstance.machine_id == machine.id)
    )
    sidecar = result.scalars().first()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if sidecar:
        sidecar.port = body.port
        sidecar.status = "alive"
        sidecar.last_heartbeat = now
        if body.version is not None:
            sidecar.version = body.version
    else:
        sidecar = SidecarInstance(
            id=uuid.uuid4(),
            machine_id=machine.id,
            port=body.port,
            status="alive",
            version=body.version,
            last_heartbeat=now,
            registered_at=now,
        )
        db.add(sidecar)

    await db.commit()
    await db.refresh(sidecar)
    return SidecarRegisterResponse(sidecar_id=sidecar.id)


@router.post("/v1/sidecars/{sidecar_id}/heartbeat", status_code=204)
async def sidecar_heartbeat(
    sidecar_id: uuid.UUID,
    body: SidecarHeartbeatRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    sidecar = await db.get(SidecarInstance, sidecar_id)
    if not sidecar:
        raise HTTPException(status_code=404, detail="Sidecar not found")
    sidecar.last_heartbeat = datetime.now(timezone.utc).replace(tzinfo=None)
    sidecar.status = "alive"
    if body and body.version is not None:
        sidecar.version = body.version
    await db.commit()


@router.post("/v1/sidecars/{sidecar_id}/deregister", status_code=204)
async def deregister_sidecar(sidecar_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    sidecar = await db.get(SidecarInstance, sidecar_id)
    if not sidecar:
        raise HTTPException(status_code=404, detail="Sidecar not found")
    sidecar.status = "dead"
    await db.commit()


# ── Topology view ─────────────────────────────────────────────────────────────

@router.get("/v1/topology", response_model=list[NamespaceTopology])
async def get_topology(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Namespace)
        .options(
            selectinload(Namespace.machines)
            .selectinload(Machine.sidecar),
            selectinload(Namespace.machines)
            .selectinload(Machine.machine_processes)
            .selectinload(MachineProcess.process_definition),
        )
        .order_by(Namespace.name)
    )
    namespaces = result.scalars().unique().all()

    topology = []
    for ns in namespaces:
        machines_out = []
        for machine in ns.machines:
            processes = [
                ProcessInTopology(
                    id=mp.id,
                    name=mp.process_definition.name,
                    log_paths=mp.log_paths,
                )
                for mp in machine.machine_processes
            ]
            machines_out.append(
                MachineInTopology(
                    machine=MachineOut.model_validate(machine),
                    sidecar=SidecarInstanceOut.model_validate(machine.sidecar) if machine.sidecar else None,
                    processes=processes,
                )
            )
        topology.append(NamespaceTopology(
            namespace=NamespaceOut.model_validate(ns),
            machines=machines_out,
        ))

    return topology


@router.get("/v1/sidecars", response_model=list[SidecarInstanceOut])
async def list_sidecars(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(SidecarInstance)
    if status and status != "all":
        q = q.where(SidecarInstance.status == status)
    result = await db.execute(q.order_by(SidecarInstance.registered_at))
    return result.scalars().all()
