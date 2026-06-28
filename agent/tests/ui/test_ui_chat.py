"""Playwright tests for the trader chat UI (/ui/chat/)."""
import httpx
import pytest
from playwright.sync_api import Page, expect


PROCESS_PAYLOAD = {
    "name": "CurveBuilder",
    "description": "Builds yield curves each morning",
    "machine_host": "server1.prod",
    "sidecar_port": 9001,
    "log_paths": ["/opt/logs/curve.log"],
    "example_qa": [],
}


@pytest.fixture
def chat_page(page: Page, live_server: str) -> Page:
    page.goto(f"{live_server}/ui/chat/")
    page.wait_for_load_state("networkidle")
    return page


def test_chat_page_title(chat_page: Page):
    expect(chat_page).to_have_title("LogSight — Trader Chat")


def test_chat_empty_state_visible(chat_page: Page):
    expect(chat_page.locator("#empty")).to_be_visible()
    expect(chat_page.locator("#empty h2")).to_have_text("Ask about your logs")


def test_chat_input_and_send_button_present(chat_page: Page):
    expect(chat_page.locator("#question")).to_be_visible()
    expect(chat_page.locator("#send-btn")).to_be_visible()
    expect(chat_page.locator("#send-btn")).to_be_enabled()


def test_chat_no_processes_returns_system_message(chat_page: Page, live_server: str):
    """When no processes are registered the agent returns a guidance message without LLM."""
    chat_page.locator("#question").fill("Is curve building done?")
    chat_page.locator("#send-btn").click()

    answer = chat_page.locator(".bubble.assistant .answer").first
    answer.wait_for(timeout=5000)
    expect(answer).to_contain_text("No processes are registered")


def test_chat_user_bubble_appears(chat_page: Page):
    chat_page.locator("#question").fill("Hello world")
    chat_page.locator("#send-btn").click()
    user_bubble = chat_page.locator(".bubble.user").first
    user_bubble.wait_for(timeout=3000)
    expect(user_bubble).to_have_text("Hello world")


def test_chat_empty_state_removed_after_send(chat_page: Page):
    chat_page.locator("#question").fill("Ping")
    chat_page.locator("#send-btn").click()
    chat_page.locator(".bubble.user").wait_for(timeout=3000)
    expect(chat_page.locator("#empty")).not_to_be_visible()


def test_chat_enter_key_submits(chat_page: Page):
    chat_page.locator("#question").fill("Any errors?")
    chat_page.locator("#question").press("Enter")
    chat_page.locator(".bubble.user").wait_for(timeout=3000)
    expect(chat_page.locator(".bubble.user").first).to_have_text("Any errors?")


def test_chat_with_registered_process_shows_answer(page: Page, live_server: str):
    """When a process exists, the LLM mock returns a summary and it renders."""
    httpx.post(f"{live_server}/v1/processes", json=PROCESS_PAYLOAD, timeout=5)

    page.goto(f"{live_server}/ui/chat/")
    page.wait_for_load_state("networkidle")

    page.locator("#question").fill("Is curve building complete?")
    page.locator("#send-btn").click()

    answer = page.locator(".bubble.assistant .answer").first
    answer.wait_for(timeout=8000)
    expect(answer).to_have_text("Test log summary from mock LLM.")


def test_chat_with_process_shows_source_chips(page: Page, live_server: str):
    """Source chips appear when the agent returns sources."""
    httpx.post(f"{live_server}/v1/processes", json=PROCESS_PAYLOAD, timeout=5)

    page.goto(f"{live_server}/ui/chat/")
    page.wait_for_load_state("networkidle")

    page.locator("#question").fill("Curve status?")
    page.locator("#send-btn").click()

    # Wait for answer bubble
    page.locator(".bubble.assistant .answer").first.wait_for(timeout=8000)
    # Source chips section should exist (even if sidecar unreachable, sources are still emitted)
    chips = page.locator(".source-chip")
    expect(chips).to_have_count(1)
    expect(chips.first.locator(".machine")).to_have_text("server1.prod")


def test_chat_question_cleared_after_send(chat_page: Page):
    chat_page.locator("#question").fill("Clear me")
    chat_page.locator("#send-btn").click()
    chat_page.locator(".bubble.user").wait_for(timeout=3000)
    expect(chat_page.locator("#question")).to_have_value("")


def test_chat_shift_enter_does_not_submit(chat_page: Page):
    chat_page.locator("#question").fill("line1")
    chat_page.locator("#question").press("Shift+Enter")
    # No user bubble should have appeared
    expect(chat_page.locator(".bubble.user")).to_have_count(0)
