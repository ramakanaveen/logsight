import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Process
from app.schemas import ChatRequest, ChatResponse, SourceInfo
from app.services import llm, fanout

router = APIRouter(prefix="/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Process))
    all_processes = result.scalars().all()

    if not all_processes:
        return ChatResponse(
            answer="No processes are registered in the system yet. Please add some processes via the admin panel.",
            sources=[],
        )

    processes_data = [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "example_qa": p.example_qa or [],
            "machine_host": p.machine_host,
            "sidecar_port": p.sidecar_port,
            "log_paths": p.log_paths,
        }
        for p in all_processes
    ]

    # LLM call 1: identify relevant processes and keywords
    try:
        routing = await asyncio.get_event_loop().run_in_executor(
            None, llm.identify_processes, body.question, processes_data
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM routing failed: {e}")

    relevant_ids = set(routing.get("relevant_process_ids", []))
    keywords = routing.get("keywords", [])

    if not relevant_ids or not keywords:
        return ChatResponse(
            answer="I couldn't identify any relevant processes for your question. Try rephrasing or check that the relevant processes are registered.",
            sources=[],
        )

    # Build fanout targets
    targets = [
        {
            "host": p["machine_host"],
            "port": p["sidecar_port"],
            "log_paths": p["log_paths"],
            "process_name": p["name"],
            "process_id": p["id"],
        }
        for p in processes_data
        if p["id"] in relevant_ids
    ]

    # Fan out to sidecars in parallel
    sidecar_results = await fanout.fanout_search(targets, keywords)

    # LLM call 2: summarize
    try:
        answer = await asyncio.get_event_loop().run_in_executor(
            None, llm.summarize_results, body.question, sidecar_results
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM summarization failed: {e}")

    # Build source info
    sources = []
    for r, t in zip(sidecar_results, targets):
        files_searched = 0
        lines_matched = 0
        if r.get("ok"):
            data = r.get("data", {})
            files_searched = data.get("total_files_searched", 0)
            for fr in data.get("results", []):
                lines_matched += fr.get("total_matched", 0)

        sources.append(SourceInfo(
            process=t["process_name"],
            machine=t["host"],
            files_searched=files_searched,
            lines_matched=lines_matched,
        ))

    return ChatResponse(answer=answer, sources=sources)
