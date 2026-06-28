"""Playwright tests for the admin process management UI (/ui/admin/)."""
import httpx
import pytest
from playwright.sync_api import Page, expect


SAMPLE = {
    "name": "CurveBuilder",
    "description": "Builds yield curves each morning",
    "machine_host": "server1.prod",
    "sidecar_port": 9001,
    "log_paths": ["/opt/logs/curve.log"],
    "example_qa": [],
}


@pytest.fixture
def admin_page(page: Page, live_server: str) -> Page:
    page.goto(f"{live_server}/ui/admin/")
    page.wait_for_load_state("networkidle")
    return page


# ─── Page structure ─────────────────────────────────────────────────────────

def test_admin_page_title(admin_page: Page):
    expect(admin_page).to_have_title("LogSight — Admin")


def test_admin_header_visible(admin_page: Page):
    expect(admin_page.locator("header h1")).to_have_text("LogSight Admin")


def test_admin_chat_link_present(admin_page: Page):
    link = admin_page.locator("header a")
    expect(link).to_have_text("Trader Chat →")
    expect(link).to_have_attribute("href", "/ui/chat/")


def test_admin_add_button_present(admin_page: Page):
    expect(admin_page.locator("button", has_text="+ Add Process")).to_be_visible()


# ─── Empty state ─────────────────────────────────────────────────────────────

def test_admin_empty_table_message(admin_page: Page):
    expect(admin_page.locator("#process-tbody")).to_contain_text("No processes registered yet.")


# ─── Modal open/close ────────────────────────────────────────────────────────

def test_admin_modal_opens_on_add_click(admin_page: Page):
    # Modal uses display:none / display:flex driven by the 'open' class.
    expect(admin_page.locator("#modal-overlay")).not_to_be_visible()
    admin_page.locator("button", has_text="+ Add Process").click()
    expect(admin_page.locator("#modal-overlay")).to_be_visible()
    expect(admin_page.locator("#modal-title")).to_have_text("Add Process")


def test_admin_modal_closes_on_cancel(admin_page: Page):
    admin_page.locator("button", has_text="+ Add Process").click()
    expect(admin_page.locator("#modal-overlay")).to_be_visible()
    admin_page.locator("button", has_text="Cancel").click()
    expect(admin_page.locator("#modal-overlay")).not_to_be_visible()


def test_admin_modal_closes_on_overlay_click(admin_page: Page):
    admin_page.locator("button", has_text="+ Add Process").click()
    expect(admin_page.locator("#modal-overlay")).to_be_visible()
    # Click the overlay backdrop (outside the modal box)
    admin_page.locator("#modal-overlay").click(position={"x": 10, "y": 10})
    expect(admin_page.locator("#modal-overlay")).not_to_be_visible()


def test_admin_modal_shows_validation_toast_on_empty_save(admin_page: Page):
    admin_page.locator("button", has_text="+ Add Process").click()
    admin_page.locator("#modal-save-btn").click()
    expect(admin_page.locator("#toast")).to_have_class("show error")
    expect(admin_page.locator("#toast")).to_contain_text("required fields")


# ─── Create process ──────────────────────────────────────────────────────────

def _fill_modal(page: Page, data: dict):
    page.locator("#f-name").fill(data.get("name", ""))
    page.locator("#f-desc").fill(data.get("description", ""))
    page.locator("#f-host").fill(data.get("machine_host", ""))
    page.locator("#f-port").fill(str(data.get("sidecar_port", 9000)))
    page.locator("#f-paths").fill("\n".join(data.get("log_paths", [])))


def test_admin_create_process_appears_in_table(admin_page: Page):
    admin_page.locator("button", has_text="+ Add Process").click()
    _fill_modal(admin_page, SAMPLE)
    admin_page.locator("#modal-save-btn").click()

    # Modal should close
    expect(admin_page.locator("#modal-overlay")).not_to_have_class("open")
    # Success toast
    expect(admin_page.locator("#toast")).to_have_class("show success")
    # Row appears in table
    expect(admin_page.locator("#process-tbody")).to_contain_text("CurveBuilder")
    expect(admin_page.locator("#process-tbody")).to_contain_text("server1.prod")


def test_admin_create_process_shows_log_path_tag(admin_page: Page):
    admin_page.locator("button", has_text="+ Add Process").click()
    _fill_modal(admin_page, SAMPLE)
    admin_page.locator("#modal-save-btn").click()
    admin_page.locator("#modal-overlay").wait_for(state="hidden")

    expect(admin_page.locator(".tag").first).to_contain_text("/opt/logs/curve.log")


def test_admin_create_process_shows_port(admin_page: Page):
    admin_page.locator("button", has_text="+ Add Process").click()
    _fill_modal(admin_page, SAMPLE)
    admin_page.locator("#modal-save-btn").click()
    admin_page.locator("#modal-overlay").wait_for(state="hidden")

    row = admin_page.locator("#process-tbody tr").first
    expect(row.locator("td").nth(2)).to_have_text("9001")


# ─── Edit process ────────────────────────────────────────────────────────────

def test_admin_edit_opens_prefilled_modal(page: Page, live_server: str):
    httpx.post(f"{live_server}/v1/processes", json=SAMPLE, timeout=5)

    page.goto(f"{live_server}/ui/admin/")
    page.wait_for_load_state("networkidle")

    page.locator("button", has_text="Edit").first.click()
    expect(page.locator("#modal-title")).to_have_text("Edit Process")
    expect(page.locator("#f-name")).to_have_value("CurveBuilder")
    expect(page.locator("#f-host")).to_have_value("server1.prod")


def test_admin_edit_updates_row(page: Page, live_server: str):
    httpx.post(f"{live_server}/v1/processes", json=SAMPLE, timeout=5)

    page.goto(f"{live_server}/ui/admin/")
    page.wait_for_load_state("networkidle")

    page.locator("button", has_text="Edit").first.click()
    page.locator("#f-host").fill("server2.prod")
    page.locator("#modal-save-btn").click()

    expect(page.locator("#toast")).to_have_class("show success")
    expect(page.locator("#toast")).to_contain_text("Process updated")
    expect(page.locator("#process-tbody")).to_contain_text("server2.prod")


# ─── QA pairs ────────────────────────────────────────────────────────────────

def test_admin_add_qa_pair_in_modal(admin_page: Page):
    admin_page.locator("button", has_text="+ Add Process").click()
    _fill_modal(admin_page, SAMPLE)

    admin_page.locator("button", has_text="+ Add Q&A").click()
    qa_pair = admin_page.locator(".qa-pair").first
    qa_pair.locator(".qa-q").fill("Is curve building complete?")
    qa_pair.locator(".qa-a").fill("Yes, completed at 14:23.")

    admin_page.locator("#modal-save-btn").click()
    expect(admin_page.locator("#toast")).to_have_class("show success")


def test_admin_remove_qa_pair(admin_page: Page):
    admin_page.locator("button", has_text="+ Add Process").click()
    _fill_modal(admin_page, SAMPLE)

    admin_page.locator("button", has_text="+ Add Q&A").click()
    admin_page.locator("button", has_text="+ Add Q&A").click()
    expect(admin_page.locator(".qa-pair")).to_have_count(2)

    admin_page.locator(".remove-qa").first.click()
    expect(admin_page.locator(".qa-pair")).to_have_count(1)


# ─── Delete process ──────────────────────────────────────────────────────────

def test_admin_delete_process_removes_row(page: Page, live_server: str):
    httpx.post(f"{live_server}/v1/processes", json=SAMPLE, timeout=5)

    page.goto(f"{live_server}/ui/admin/")
    page.wait_for_load_state("networkidle")
    expect(page.locator("#process-tbody")).to_contain_text("CurveBuilder")

    # Accept the confirm() dialog before clicking Delete
    page.once("dialog", lambda d: d.accept())
    page.locator("button", has_text="Delete").first.click()

    expect(page.locator("#toast")).to_have_class("show success")
    expect(page.locator("#toast")).to_contain_text("deleted")
    expect(page.locator("#process-tbody")).to_contain_text("No processes registered yet.")


def test_admin_delete_cancel_keeps_row(page: Page, live_server: str):
    httpx.post(f"{live_server}/v1/processes", json=SAMPLE, timeout=5)

    page.goto(f"{live_server}/ui/admin/")
    page.wait_for_load_state("networkidle")

    # Dismiss the confirm() dialog (Cancel)
    page.once("dialog", lambda d: d.dismiss())
    page.locator("button", has_text="Delete").first.click()

    # Row still present
    expect(page.locator("#process-tbody")).to_contain_text("CurveBuilder")


# ─── Multi-process table ─────────────────────────────────────────────────────

def test_admin_multiple_processes_in_table(page: Page, live_server: str):
    httpx.post(f"{live_server}/v1/processes", json=SAMPLE, timeout=5)
    httpx.post(
        f"{live_server}/v1/processes",
        json={**SAMPLE, "name": "RiskEngine", "machine_host": "server2.prod"},
        timeout=5,
    )

    page.goto(f"{live_server}/ui/admin/")
    page.wait_for_load_state("networkidle")

    rows = page.locator("#process-tbody tr")
    expect(rows).to_have_count(2)
    expect(page.locator("#process-tbody")).to_contain_text("CurveBuilder")
    expect(page.locator("#process-tbody")).to_contain_text("RiskEngine")
