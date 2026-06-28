"""Chat route: SSE streaming agentic loop + backward-compat non-streaming endpoint."""
import json
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ProcessDefinition, Conversation, Message
from app.schemas import ChatRequest, ChatResponse, SourceInfo
from app.services.agent import run_agent, ClarifyPause

router = APIRouter(prefix="/v1/chat", tags=["chat"])


async def _get_or_create_conversation(
    conversation_id: uuid.UUID | None, db: AsyncSession
) -> Conversation:
    if conversation_id:
        conv = await db.get(Conversation, conversation_id)
        if conv:
            return conv
    conv = Conversation(id=uuid.uuid4(), title="")
    db.add(conv)
    await db.flush()
    return conv


async def _load_history(conv: Conversation, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    # Plain text only — avoids SDK object serialization issues and is always valid
    # for the Anthropic API. Tool-call details from prior turns are not needed for context.
    return [{"role": m.role, "content": m.content} for m in messages]


async def _save_turn(
    conv: Conversation, question: str, answer: str, final_messages: list[dict], db: AsyncSession
) -> None:
    if not conv.title:
        conv.title = question[:80]

    user_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        role="user",
        content=question,
        metadata_={},
    )
    assistant_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        role="assistant",
        content=answer,
        metadata_={},
    )
    db.add(user_msg)
    db.add(assistant_msg)
    conv.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()


def _sse(event_type: str, data: object) -> str:
    return f"data: {json.dumps({'type': event_type, 'data': data})}\n\n"


async def _stream_agent(
    body: ChatRequest, db: AsyncSession
) -> AsyncGenerator[str, None]:
    result = await db.execute(select(ProcessDefinition))
    all_pds = result.scalars().all()
    process_definitions = [
        {"name": p.name, "description": p.description, "example_qa": p.example_qa or []}
        for p in all_pds
    ]

    conv = await _get_or_create_conversation(body.conversation_id, db)
    history = await _load_history(conv, db)

    collected: list[str] = []

    async def emit(event_type: str, data: object) -> None:
        collected.append(_sse(event_type, data))

    events: list[str] = []

    try:
        answer, final_messages = await run_agent(
            question=body.question,
            process_hint=body.process_hint,
            history=history,
            process_definitions=process_definitions,
            db=db,
            emit=emit,
        )
        events = collected
        await _save_turn(conv, body.question, answer, final_messages, db)
        events.append(_sse("sources", []))
        events.append(_sse("done", {"conversation_id": str(conv.id)}))
    except ClarifyPause as cp:
        events = collected
        events.append(_sse("done", {"conversation_id": str(conv.id), "clarify": True}))
    except Exception as e:
        events = collected
        events.append(_sse("error", {"message": str(e)}))

    for event in events:
        yield event


@router.post("/stream")
async def chat_stream(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """SSE streaming: emits thinking, tool_call, tool_result, clarify, answer, sources, done."""
    return StreamingResponse(
        _stream_agent(body, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Non-streaming endpoint (backward compat). Collects the full answer before returning."""
    result = await db.execute(select(ProcessDefinition))
    all_pds = result.scalars().all()
    if not all_pds:
        conv = await _get_or_create_conversation(body.conversation_id, db)
        return ChatResponse(
            answer="No processes are registered yet. Add some via the admin UI.",
            sources=[],
            conversation_id=conv.id,
        )

    process_definitions = [
        {"name": p.name, "description": p.description, "example_qa": p.example_qa or []}
        for p in all_pds
    ]
    conv = await _get_or_create_conversation(body.conversation_id, db)
    history = await _load_history(conv, db)
    events: list[tuple[str, object]] = []

    async def emit(event_type: str, data: object) -> None:
        events.append((event_type, data))

    try:
        answer, final_messages = await run_agent(
            question=body.question,
            process_hint=body.process_hint,
            history=history,
            process_definitions=process_definitions,
            db=db,
            emit=emit,
        )
    except ClarifyPause as cp:
        answer = f"I need more information: {cp.question}"
        final_messages = cp.messages

    await _save_turn(conv, body.question, answer, final_messages, db)

    sources = [
        SourceInfo(
            process=e[1].get("process_name", ""),
            machine="",
            files_searched=e[1].get("files_searched", 0),
            lines_matched=e[1].get("lines_matched", 0),
        )
        for e in events
        if e[0] == "tool_result" and isinstance(e[1], dict) and "process_name" in e[1]
    ]

    return ChatResponse(answer=answer, sources=sources, conversation_id=conv.id)
