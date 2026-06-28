import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ProcessDefinition
from app.schemas import ProcessDefinitionCreate, ProcessDefinitionOut, ProcessDefinitionUpdate

router = APIRouter(prefix="/v1/processes", tags=["processes"])


@router.get("", response_model=list[ProcessDefinitionOut])
async def list_processes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProcessDefinition).order_by(ProcessDefinition.name))
    return result.scalars().all()


@router.post("", response_model=ProcessDefinitionOut, status_code=201)
async def create_process(body: ProcessDefinitionCreate, db: AsyncSession = Depends(get_db)):
    pd = ProcessDefinition(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
        example_qa=[qa.model_dump() for qa in body.example_qa],
    )
    db.add(pd)
    await db.commit()
    await db.refresh(pd)
    return pd


@router.put("/{process_id}", response_model=ProcessDefinitionOut)
async def update_process(
    process_id: uuid.UUID, body: ProcessDefinitionUpdate, db: AsyncSession = Depends(get_db)
):
    pd = await db.get(ProcessDefinition, process_id)
    if not pd:
        raise HTTPException(status_code=404, detail="Process not found")
    for field, value in body.model_dump(exclude_none=True).items():
        if field == "example_qa" and value is not None:
            value = [qa if isinstance(qa, dict) else qa.model_dump() for qa in value]
        setattr(pd, field, value)
    await db.commit()
    await db.refresh(pd)
    return pd


@router.delete("/{process_id}", status_code=204)
async def delete_process(process_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    pd = await db.get(ProcessDefinition, process_id)
    if not pd:
        raise HTTPException(status_code=404, detail="Process not found")
    await db.delete(pd)
    await db.commit()
