import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Process
from app.schemas import ProcessCreate, ProcessOut, ProcessUpdate

router = APIRouter(prefix="/v1/processes", tags=["processes"])


@router.get("", response_model=list[ProcessOut])
async def list_processes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Process).order_by(Process.name))
    return result.scalars().all()


@router.post("", response_model=ProcessOut, status_code=201)
async def create_process(body: ProcessCreate, db: AsyncSession = Depends(get_db)):
    process = Process(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
        machine_host=body.machine_host,
        sidecar_port=body.sidecar_port,
        log_paths=body.log_paths,
        example_qa=[qa.model_dump() for qa in body.example_qa],
    )
    db.add(process)
    await db.commit()
    await db.refresh(process)
    return process


@router.put("/{process_id}", response_model=ProcessOut)
async def update_process(process_id: uuid.UUID, body: ProcessUpdate, db: AsyncSession = Depends(get_db)):
    process = await db.get(Process, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    for field, value in body.model_dump(exclude_none=True).items():
        if field == "example_qa" and value is not None:
            value = [qa if isinstance(qa, dict) else qa.model_dump() for qa in value]
        setattr(process, field, value)

    await db.commit()
    await db.refresh(process)
    return process


@router.delete("/{process_id}", status_code=204)
async def delete_process(process_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    process = await db.get(Process, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    await db.delete(process)
    await db.commit()
