"""
Multi-turn agentic loop using Claude tool-use + extended thinking.

Claude is given three tools:
  list_sidecars  — query alive sidecars from the DB
  search_logs    — call a sidecar /search endpoint for a named process
  ask_user       — emit a clarify SSE event and pause (next turn resumes)

The loop runs until Claude produces stop_reason="end_turn".
Each iteration streams SSE events via the `emit` callback.
"""
import asyncio
import json
import uuid
from collections.abc import Callable, Awaitable
from datetime import datetime, timezone
from typing import Any

import anthropic
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import SidecarInstance, Machine, MachineProcess, ProcessDefinition
from app.services.fanout import query_sidecar_raw

_anthropic: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _anthropic
    if _anthropic is None:
        _anthropic = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _anthropic


TOOLS: list[dict] = [
    {
        "name": "list_sidecars",
        "description": (
            "List alive sidecars filtered by namespace, machine hostname, or process name. "
            "Use this first to discover where logs for a process might live."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace name, e.g. STIRT, SPOT"},
                "machine_host": {"type": "string", "description": "Exact or partial hostname"},
                "process_name": {"type": "string", "description": "Process name, e.g. CurveBuilder"},
                "status": {
                    "type": "string",
                    "enum": ["alive", "dead", "all"],
                    "description": "Filter by sidecar liveness. Default: alive",
                },
            },
        },
    },
    {
        "name": "search_logs",
        "description": (
            "Search log files for a specific process on a machine via its sidecar. "
            "The server resolves the log paths from the MachineProcess registry. "
            "Call multiple times with different keywords or time windows to dig deeper."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sidecar_id": {"type": "string", "description": "UUID of the SidecarInstance"},
                "process_name": {
                    "type": "string",
                    "description": "Name of the process whose logs to search (e.g. CurveBuilder)",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to grep in log lines",
                },
                "time_window_minutes": {
                    "type": "integer",
                    "description": "How far back to look in minutes. Omit to search all available logs.",
                },
                "max_lines": {"type": "integer", "description": "Max matched lines to return. Default 50"},
            },
            "required": ["sidecar_id", "process_name", "keywords"],
        },
    },
    {
        "name": "ask_user",
        "description": (
            "Ask the user a clarifying question when the request is ambiguous "
            "(e.g. no time range given, unclear which system). "
            "This pauses the loop — the user's reply becomes the next turn."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
            },
            "required": ["question"],
        },
    },
]


def _build_system_prompt(process_definitions: list[dict]) -> str:
    pd_json = json.dumps(
        [{"name": p["name"], "description": p["description"], "example_qa": p.get("example_qa", [])}
         for p in process_definitions],
        indent=2,
    )
    return f"""You are a log intelligence assistant for a trading firm.

Registered processes and their descriptions:
{pd_json}

Your job: answer the trader's question by searching the right log files.

Workflow:
1. Call list_sidecars to find alive sidecars (filter by namespace/process if you know them).
2. Call search_logs for each relevant sidecar+process combination.
3. If the question is ambiguous (no time range, unclear system), call ask_user ONCE.
4. When you have enough evidence, write a concise plain-English answer.

Be specific about times, machines, and statuses when the data supports it.
If no relevant logs were found, say so clearly.
"""


def _build_user_content(question: str, process_hint: str | None) -> str:
    if process_hint:
        return f"[Process hint: {process_hint}]\n\n{question}"
    return question


async def run_agent(
    *,
    question: str,
    process_hint: str | None,
    history: list[dict],
    process_definitions: list[dict],
    db: AsyncSession,
    emit: Callable[[str, Any], Awaitable[None]],
) -> tuple[str, list[dict]]:
    """
    Run the agentic loop.

    Returns (answer_text, updated_messages_list).
    `emit(event_type, data)` is called for every SSE event.
    Raises `ClarifyPause` with the question when ask_user is called.
    """
    messages: list[dict] = [
        *history,
        {"role": "user", "content": _build_user_content(question, process_hint)},
    ]
    system = _build_system_prompt(process_definitions)
    answer_text = ""
    sources: list[dict] = []

    while True:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: _get_client().messages.create(
                model=settings.model,
                system=system,
                tools=TOOLS,
                thinking={"type": "enabled", "budget_tokens": 5000},
                max_tokens=8096,
                messages=messages,
            ),
        )

        # Emit thinking and answer blocks
        for block in response.content:
            if block.type == "thinking":
                await emit("thinking", {"text": block.thinking})
            elif block.type == "text" and response.stop_reason == "end_turn":
                answer_text = block.text
                await emit("answer", {"text": block.text})

        if response.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": response.content})
            break

        # Execute tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            await emit("tool_call", {"tool": block.name, "input": block.input})

            if block.name == "ask_user":
                await emit("clarify", {"question": block.input["question"]})
                raise ClarifyPause(
                    question=block.input["question"],
                    messages=messages + [{"role": "assistant", "content": response.content}],
                )

            result = await _execute_tool(block.name, block.input, db, sources)
            await emit("tool_result", {"tool": block.name, "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return answer_text, messages


async def _execute_tool(
    name: str,
    input_: dict,
    db: AsyncSession,
    sources: list[dict],
) -> Any:
    if name == "list_sidecars":
        return await _tool_list_sidecars(input_, db)
    if name == "search_logs":
        result = await _tool_search_logs(input_, db)
        sources.append({
            "sidecar_id": input_["sidecar_id"],
            "process_name": input_["process_name"],
            "lines_matched": sum(r.get("total_matched", 0) for r in result.get("results", [])),
            "files_searched": result.get("total_files_searched", 0),
        })
        return result
    return {"error": f"Unknown tool: {name}"}


async def _tool_list_sidecars(input_: dict, db: AsyncSession) -> list[dict]:
    q = (
        select(SidecarInstance)
        .options(
            selectinload(SidecarInstance.machine).selectinload(Machine.namespace),
            selectinload(SidecarInstance.machine)
            .selectinload(Machine.machine_processes)
            .selectinload(MachineProcess.process_definition),
        )
    )

    status_filter = input_.get("status", "alive")
    if status_filter != "all":
        q = q.where(SidecarInstance.status == status_filter)

    result = await db.execute(q)
    sidecars = result.scalars().unique().all()

    out = []
    for s in sidecars:
        machine = s.machine
        ns_name = machine.namespace.name if machine.namespace else ""
        if input_.get("namespace") and input_["namespace"].lower() not in ns_name.lower():
            continue
        if input_.get("machine_host") and input_["machine_host"].lower() not in machine.hostname.lower():
            continue

        processes = [mp.process_definition.name for mp in machine.machine_processes]
        if input_.get("process_name"):
            hint = input_["process_name"].lower()
            if not any(hint in p.lower() for p in processes):
                continue

        out.append({
            "sidecar_id": str(s.id),
            "machine_host": machine.hostname,
            "namespace": ns_name,
            "port": s.port,
            "status": s.status,
            "last_heartbeat": s.last_heartbeat.isoformat() if s.last_heartbeat else None,
            "processes": processes,
        })

    return out


async def _tool_search_logs(input_: dict, db: AsyncSession) -> dict:
    try:
        sidecar_id = uuid.UUID(input_["sidecar_id"])
    except ValueError:
        return {"error": "Invalid sidecar_id"}

    sidecar = await db.get(
        SidecarInstance,
        sidecar_id,
        options=[
            selectinload(SidecarInstance.machine)
            .selectinload(Machine.machine_processes)
            .selectinload(MachineProcess.process_definition)
        ],
    )
    if not sidecar:
        return {"error": f"Sidecar {input_['sidecar_id']} not found"}
    if sidecar.status == "dead":
        return {"error": f"Sidecar on {sidecar.machine.hostname} is dead (last heartbeat: {sidecar.last_heartbeat})"}

    # Resolve log paths from MachineProcess
    process_name = input_["process_name"]
    log_paths: list[str] = []
    for mp in sidecar.machine.machine_processes:
        if mp.process_definition.name.lower() == process_name.lower():
            log_paths = mp.log_paths
            break

    if not log_paths:
        return {"error": f"No log paths registered for process {process_name!r} on {sidecar.machine.hostname}"}

    payload: dict[str, Any] = {
        "keywords": input_["keywords"],
        "log_paths": log_paths,
        "max_lines": input_.get("max_lines", 50),
    }
    if "time_window_minutes" in input_:
        payload["time_window_minutes"] = input_["time_window_minutes"]

    return await query_sidecar_raw(sidecar.machine.hostname, sidecar.port, payload)


class ClarifyPause(Exception):
    """Raised when the agent calls ask_user — signals the chat route to pause and return."""
    def __init__(self, question: str, messages: list[dict]):
        self.question = question
        self.messages = messages
        super().__init__(question)
