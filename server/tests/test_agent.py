"""Tests for the agentic loop (run_agent) with fully mocked Anthropic API and sidecars."""
import uuid
import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.agent import run_agent, ClarifyPause

pytestmark = pytest.mark.anyio


def _make_content_block(type_: str, **kwargs):
    """Build a minimal mock content block."""
    b = MagicMock()
    b.type = type_
    for k, v in kwargs.items():
        setattr(b, k, v)
    return b


def _make_response(content: list, stop_reason: str = "end_turn"):
    r = MagicMock()
    r.content = content
    r.stop_reason = stop_reason
    r.usage.input_tokens = 100
    r.usage.output_tokens = 50
    return r


def _make_anthropic_mock(responses: list):
    """Return a mock client whose messages.create() returns responses in sequence."""
    client = MagicMock()
    client.messages.create.side_effect = responses
    return client


async def test_agent_single_turn_end_turn(db_session):
    """Agent receives end_turn immediately — returns answer without tool calls."""
    text_block = _make_content_block("text", text="Curve building is done.")
    response = _make_response([text_block], stop_reason="end_turn")

    events = []

    async def emit(event_type, data):
        events.append((event_type, data))

    with patch("app.services.agent._get_client", return_value=_make_anthropic_mock([response])):
        answer, messages, sources = await run_agent(
            question="Is curve building done?",
            process_hint=None,
            history=[],
            process_definitions=[{"name": "CurveBuilder", "description": "Builds curves", "example_qa": []}],
            db=db_session,
            emit=emit,
        )

    assert answer == "Curve building is done."
    assert any(e[0] == "answer" for e in events)
    assert any(e[0] == "usage" for e in events)


async def test_agent_thinking_block_emitted(db_session):
    """Thinking blocks are emitted as SSE events."""
    thinking_block = _make_content_block("thinking", thinking="Let me check the sidecars.")
    text_block = _make_content_block("text", text="Done.")
    response = _make_response([thinking_block, text_block], stop_reason="end_turn")

    events = []

    async def emit(event_type, data):
        events.append((event_type, data))

    with patch("app.services.agent._get_client", return_value=_make_anthropic_mock([response])):
        await run_agent(
            question="Is it done?",
            process_hint=None,
            history=[],
            process_definitions=[],
            db=db_session,
            emit=emit,
        )

    thinking_events = [e for e in events if e[0] == "thinking"]
    assert len(thinking_events) == 1
    assert "sidecars" in thinking_events[0][1]["text"]


async def test_agent_tool_call_then_end_turn(db_session, machine_process, sidecar, namespace, machine, created_process):
    """Agent calls list_sidecars, gets result, then ends turn."""
    tool_block = _make_content_block(
        "tool_use",
        id="t1",
        name="list_sidecars",
        input={"status": "alive"},
    )
    r1 = _make_response([tool_block], stop_reason="tool_use")

    text_block = _make_content_block("text", text="Found 1 sidecar.")
    r2 = _make_response([text_block], stop_reason="end_turn")

    events = []

    async def emit(event_type, data):
        events.append((event_type, data))

    with patch("app.services.agent._get_client", return_value=_make_anthropic_mock([r1, r2])):
        answer, _, _sources = await run_agent(
            question="Which sidecars are alive?",
            process_hint=None,
            history=[],
            process_definitions=[],
            db=db_session,
            emit=emit,
        )

    tool_calls = [e for e in events if e[0] == "tool_call"]
    tool_results = [e for e in events if e[0] == "tool_result"]
    assert len(tool_calls) == 1
    assert tool_calls[0][1]["tool"] == "list_sidecars"
    assert len(tool_results) == 1


async def test_agent_ask_user_raises_clarify_pause(db_session):
    """When ask_user is called, ClarifyPause is raised with the question."""
    tool_block = _make_content_block(
        "tool_use",
        id="t1",
        name="ask_user",
        input={"question": "Which time range?"},
    )
    r1 = _make_response([tool_block], stop_reason="tool_use")

    events = []

    async def emit(event_type, data):
        events.append((event_type, data))

    with patch("app.services.agent._get_client", return_value=_make_anthropic_mock([r1])):
        with pytest.raises(ClarifyPause) as exc_info:
            await run_agent(
                question="What happened?",
                process_hint=None,
                history=[],
                process_definitions=[],
                db=db_session,
                emit=emit,
            )

    assert exc_info.value.question == "Which time range?"
    assert any(e[0] == "clarify" for e in events)


async def test_agent_with_process_hint(db_session):
    """process_hint is prepended to the user message."""
    text_block = _make_content_block("text", text="CurveBuilder is done.")
    response = _make_response([text_block], stop_reason="end_turn")

    captured_messages = []

    def fake_create(**kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        return response

    client_mock = MagicMock()
    client_mock.messages.create.side_effect = fake_create

    async def _noop_emit(*a):
        pass

    with patch("app.services.agent._get_client", return_value=client_mock):
        await run_agent(
            question="Is it done?",
            process_hint="CurveBuilder",
            history=[],
            process_definitions=[],
            db=db_session,
            emit=_noop_emit,
        )

    user_content = captured_messages[0]["content"]
    assert "CurveBuilder" in user_content


async def test_agent_multi_turn_history_included(db_session):
    """History messages are prepended to the messages list."""
    text_block = _make_content_block("text", text="Following up.")
    response = _make_response([text_block], stop_reason="end_turn")

    captured_messages = []

    def fake_create(**kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        return response

    client_mock = MagicMock()
    client_mock.messages.create.side_effect = fake_create

    history = [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
    ]

    async def _noop_emit(*a):
        pass

    with patch("app.services.agent._get_client", return_value=client_mock):
        await run_agent(
            question="Follow-up question",
            process_hint=None,
            history=history,
            process_definitions=[],
            db=db_session,
            emit=_noop_emit,
        )

    assert captured_messages[0]["content"] == "First question"
    assert captured_messages[1]["content"] == "First answer"
    assert "Follow-up" in captured_messages[2]["content"]


async def test_agent_usage_event_emitted(db_session):
    """usage SSE event is emitted with accumulated token counts after end_turn."""
    text_block = _make_content_block("text", text="Answer.")
    response = _make_response([text_block], stop_reason="end_turn")
    response.usage.input_tokens = 200
    response.usage.output_tokens = 75

    events = []

    async def emit(event_type, data):
        events.append((event_type, data))

    with patch("app.services.agent._get_client", return_value=_make_anthropic_mock([response])):
        await run_agent(
            question="Any question",
            process_hint=None,
            history=[],
            process_definitions=[],
            db=db_session,
            emit=emit,
        )

    usage_events = [e for e in events if e[0] == "usage"]
    assert len(usage_events) == 1
    u = usage_events[0][1]
    assert u["input_tokens"] == 200
    assert u["output_tokens"] == 75
    assert u["total_tokens"] == 275
    assert u["cost_usd"] > 0


async def test_agent_ask_user_with_options(db_session):
    """ask_user with options emits clarify event with the options list."""
    tool_block = _make_content_block(
        "tool_use",
        id="t1",
        name="ask_user",
        input={"question": "Which process?", "options": ["CurveBuilder", "RiskEngine"]},
    )
    r1 = _make_response([tool_block], stop_reason="tool_use")

    events = []

    async def emit(event_type, data):
        events.append((event_type, data))

    with patch("app.services.agent._get_client", return_value=_make_anthropic_mock([r1])):
        with pytest.raises(ClarifyPause):
            await run_agent(
                question="Check the process",
                process_hint=None,
                history=[],
                process_definitions=[],
                db=db_session,
                emit=emit,
            )

    clarify_events = [e for e in events if e[0] == "clarify"]
    assert len(clarify_events) == 1
    assert clarify_events[0][1]["options"] == ["CurveBuilder", "RiskEngine"]


async def test_agent_render_chart_emits_chart_event(db_session):
    """render_chart tool call emits chart SSE event without calling any sidecar."""
    chart_spec = {
        "chart_type": "bar",
        "title": "Errors by Hour",
        "labels": ["10:00", "11:00", "12:00"],
        "datasets": [{"label": "Errors", "data": [3, 7, 1]}],
    }
    chart_block = _make_content_block("tool_use", id="t1", name="render_chart", input=chart_spec)
    r1 = _make_response([chart_block], stop_reason="tool_use")

    text_block = _make_content_block("text", text="Chart shown above.")
    r2 = _make_response([text_block], stop_reason="end_turn")

    events = []

    async def emit(event_type, data):
        events.append((event_type, data))

    with patch("app.services.agent._get_client", return_value=_make_anthropic_mock([r1, r2])):
        answer, _, sources = await run_agent(
            question="Show me a chart",
            process_hint=None,
            history=[],
            process_definitions=[],
            db=db_session,
            emit=emit,
        )

    chart_events = [e for e in events if e[0] == "chart"]
    assert len(chart_events) == 1
    assert chart_events[0][1]["chart_type"] == "bar"


async def test_agent_search_logs_arbitrary_log_paths(db_session, sidecar, machine):
    """search_logs with explicit log_paths bypasses MachineProcess registry."""
    import uuid as uuid_mod

    sidecar_id = sidecar["sidecar_id"]

    tool_block = _make_content_block(
        "tool_use",
        id="t1",
        name="search_logs",
        input={
            "sidecar_id": sidecar_id,
            "process_name": "Unknown",
            "keywords": ["error"],
            "log_paths": ["/var/log/custom.log"],
        },
    )
    r1 = _make_response([tool_block], stop_reason="tool_use")
    text_block = _make_content_block("text", text="Found in custom log.")
    r2 = _make_response([text_block], stop_reason="end_turn")

    events = []

    async def emit(event_type, data):
        events.append((event_type, data))

    sidecar_result = {
        "results": [{"path": "/var/log/custom.log", "matched_lines": [], "total_matched": 2, "error": None}],
        "total_files_searched": 1,
    }

    with patch("app.services.agent._get_client", return_value=_make_anthropic_mock([r1, r2])), \
         patch("app.services.agent.query_sidecar_raw", return_value=sidecar_result):
        answer, _, sources = await run_agent(
            question="Search /var/log/custom.log on server1",
            process_hint=None,
            history=[],
            process_definitions=[],
            db=db_session,
            emit=emit,
        )

    # Should not error out with "No log paths registered" — instead should succeed
    tool_results = [e for e in events if e[0] == "tool_result"]
    assert len(tool_results) == 1
    result = tool_results[0][1]["result"]
    # The result is the raw sidecar payload (which has "error": None per file — that's OK).
    # We just check it's not a top-level error string.
    assert "No log paths" not in str(result)
    assert isinstance(result, dict)
