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
            "The server resolves the log paths from the MachineProcess registry unless you supply log_paths directly. "
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
                "log_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional. Explicit glob patterns to search "
                        "(e.g. ['/var/log/app.log', '/tmp/*.log']). "
                        "If omitted, paths are resolved from the MachineProcess registry using process_name. "
                        "Use this when the user specifies a file path directly."
                    ),
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
        "name": "render_chart",
        "description": (
            "Render a chart in the UI. Call this after search_logs when the answer is better shown "
            "as a visualization (frequency counts, time series, comparisons across machines). "
            "Derive the chart data yourself from the log lines you received. "
            "You can also call this proactively when the data is inherently comparative."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie"],
                    "description": "Chart type",
                },
                "title": {"type": "string", "description": "Chart title"},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "X-axis labels (bar/line) or slice names (pie)",
                },
                "datasets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "data": {"type": "array", "items": {"type": "number"}},
                        },
                        "required": ["label", "data"],
                    },
                    "description": "One dataset per series",
                },
            },
            "required": ["chart_type", "title", "labels", "datasets"],
        },
    },
    {
        "name": "ask_user",
        "description": (
            "Ask the user a clarifying question when the request is ambiguous "
            "(e.g. no time range given, unclear which system). "
            "This pauses the loop — the user's reply becomes the next turn. "
            "Supply options[] when the ambiguity has a known set of choices (e.g. process names)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of choices to present as buttons (e.g. process names)",
                },
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
   - Supply options[] when the ambiguity has a known set of choices (e.g. list process names as buttons).
4. When you have enough evidence, write a concise plain-English answer using markdown.
   - Use tables when comparing data across machines or processes.
   - Use bold for key findings, times, and machine names.

Arbitrary log file search:
- If the user specifies a file path directly (e.g. "search /var/log/app.log on server1"):
  1. Call list_sidecars(machine_host="server1") to find the sidecar.
  2. Call search_logs with log_paths=["/var/log/app.log"] — the process_name is optional in this case.

CRITICAL — proactive anomaly detection:
- If any log line contains: shutdown / terminated / SIGTERM / SIGKILL / exit code / crashed / killed / OOM:
  → Start your answer with "⚠️ Process appears to have shut down" and explain what the logs show.
  → Do NOT bury this finding in a summary — call it out FIRST.
- If a sidecar is dead (status=dead) and logs indicate a shutdown:
  → Flag the process as "likely offline" at the top of your answer.

Be specific about times, machines, and statuses when the data supports it.
If no relevant logs were found, say so clearly.
"""


def _build_user_content(question: str, process_hint: str | None) -> str:
    if process_hint:
        return f"[Process hint: {process_hint}]\n\n{question}"
    return question


_SONNET_INPUT_PER_TOKEN = 3 / 1_000_000   # $3 per million input tokens
_SONNET_OUTPUT_PER_TOKEN = 15 / 1_000_000  # $15 per million output tokens


async def run_agent(
    *,
    question: str,
    process_hint: str | None,
    history: list[dict],
    process_definitions: list[dict],
    db: AsyncSession,
    emit: Callable[[str, Any], Awaitable[None]],
) -> tuple[str, list[dict], list[dict]]:
    """
    Run the agentic loop.

    Returns (answer_text, updated_messages_list, sources_list).
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
    total_input = 0
    total_output = 0

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

        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens

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
                await emit("clarify", {
                    "question": block.input["question"],
                    "options": block.input.get("options", []),
                })
                raise ClarifyPause(
                    question=block.input["question"],
                    messages=messages + [{"role": "assistant", "content": response.content}],
                )

            if block.name == "render_chart":
                await emit("chart", block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Chart rendered in UI.",
                })
                continue

            result = await _execute_tool(block.name, block.input, db, sources)
            await emit("tool_result", {"tool": block.name, "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    cost = round(
        total_input * _SONNET_INPUT_PER_TOKEN + total_output * _SONNET_OUTPUT_PER_TOKEN,
        5,
    )
    await emit("usage", {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "cost_usd": cost,
    })

    return answer_text, messages, sources


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
        if "error" not in result:
            sources.append({
                "sidecar_id": input_["sidecar_id"],
                "process_name": input_["process_name"],
                "machine_host": result.get("_machine_host", ""),
                "lines_matched": sum(r.get("total_matched", 0) for r in result.get("results", [])),
                "files_searched": result.get("total_files_searched", 0),
                "matched_files": [
                    r["path"] for r in result.get("results", []) if r.get("total_matched", 0) > 0
                ],
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

    process_name = input_["process_name"]

    # Use caller-supplied paths if provided; otherwise resolve from MachineProcess registry
    log_paths: list[str] = input_.get("log_paths") or []
    if not log_paths:
        for mp in sidecar.machine.machine_processes:
            if mp.process_definition.name.lower() == process_name.lower():
                log_paths = mp.log_paths
                break

    if not log_paths:
        return {
            "error": (
                f"No log paths registered for process {process_name!r} on {sidecar.machine.hostname}. "
                "Provide log_paths explicitly or register the process in Admin."
            )
        }

    payload: dict[str, Any] = {
        "keywords": input_["keywords"],
        "log_paths": log_paths,
        "max_lines": input_.get("max_lines", 50),
    }
    if "time_window_minutes" in input_:
        payload["time_window_minutes"] = input_["time_window_minutes"]

    result = await query_sidecar_raw(sidecar.machine.hostname, sidecar.port, payload)
    if isinstance(result, dict) and "error" not in result:
        result["_machine_host"] = sidecar.machine.hostname
    return result


class ClarifyPause(Exception):
    """Raised when the agent calls ask_user — signals the chat route to pause and return."""
    def __init__(self, question: str, messages: list[dict]):
        self.question = question
        self.messages = messages
        super().__init__(question)
