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
        answer, messages = await run_agent(
            question="Is curve building done?",
            process_hint=None,
            history=[],
            process_definitions=[{"name": "CurveBuilder", "description": "Builds curves", "example_qa": []}],
            db=db_session,
            emit=emit,
        )

    assert answer == "Curve building is done."
    assert any(e[0] == "answer" for e in events)


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
        answer, _ = await run_agent(
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
