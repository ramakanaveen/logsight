"""Feedback routes: POST /v1/feedback (submit rating), GET /v1/feedback (admin list)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Feedback, Conversation, Message
from app.schemas import FeedbackCreate, FeedbackOut

router = APIRouter(prefix="/v1/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut, status_code=201)
async def submit_feedback(body: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    if body.rating not in (1, -1):
        raise HTTPException(status_code=422, detail="rating must be 1 or -1")
    conv = await db.get(Conversation, body.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msg = await db.get(Message, body.message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    fb = Feedback(
        id=uuid.uuid4(),
        conversation_id=body.conversation_id,
        message_id=body.message_id,
        rating=body.rating,
        comment=body.comment,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb


@router.get("", response_model=list[FeedbackOut])
async def list_feedback(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feedback).order_by(Feedback.created_at.desc()))
    return result.scalars().all()
