"""End-to-end UI tests for the share / unshare flow on the client page.

Covers the user journey:
- therapist clicks a client row → lands on the per-client page
- therapist shares with a real psychiatrist → "Shared with X" + Unshare appear
- therapist tries an unknown psychiatrist email → error, no shared-with line
- therapist unshares → share form returns
- psychiatrist on a shared client page does NOT see share controls

Per-input validation lives in the API tests; this file focuses on what the
user actually sees and clicks.
"""

from playwright.sync_api import Page, expect

from pages.client_page import ClientPage
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage


def test_therapist_navigates_from_dashboard_to_client_page(
    page: Page, therapist_user, therapist_client
):
    """Clicking a client row in the dashboard must land on /clients/:id
    with the client's full name as the page header."""
    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])

    DashboardPage(page).client_list.wait_for()
    page.get_by_test_id("client-link").first.click()

    client_page = ClientPage(page)
    expect(client_page.header).to_have_text(
        f"{therapist_client['first_name']} {therapist_client['last_name']}"
    )


def test_share_confirmation_shows_psychiatrist_name(
    page: Page, therapist_user, therapist_client, psychiatrist_user
):
    """Submitting a real psychiatrist email must show the confirmation
    panel with their full name and email — that's the whole point of
    the two-step flow: the therapist sees who they're about to share
    with before committing. No share happens at this stage."""
    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])

    client_page = ClientPage(page)
    client_page.goto(therapist_client["id"])
    client_page.start_share(psychiatrist_user["email"])

    expect(client_page.share_confirm_block).to_be_visible()
    expect(client_page.share_confirm_name).to_have_text(
        f"{psychiatrist_user['first_name']} {psychiatrist_user['last_name']}"
    )
    expect(client_page.share_confirm_email).to_have_text(psychiatrist_user["email"])
    # No share has occurred yet — shared-with block must not be present
    expect(client_page.shared_with_block).not_to_be_visible()


def test_cancel_share_returns_to_input_form(
    page: Page, therapist_user, therapist_client, psychiatrist_user
):
    """Clicking Cancel on the confirmation must return to the email input,
    NOT commit the share. This protects against accidental shares that
    silently confirm if the cancel path is broken."""
    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])

    client_page = ClientPage(page)
    client_page.goto(therapist_client["id"])
    client_page.start_share(psychiatrist_user["email"])
    expect(client_page.share_confirm_block).to_be_visible()

    client_page.cancel_share()

    expect(client_page.share_confirm_block).not_to_be_visible()
    expect(client_page.share_form).to_be_visible()
    expect(client_page.shared_with_block).not_to_be_visible()


def test_therapist_shares_client_with_psychiatrist(
    page: Page, therapist_user, therapist_client, psychiatrist_user
):
    """Full two-step flow: enter email → confirmation panel → confirm →
    'Shared with [name] (email)' line + Unshare button."""
    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])

    client_page = ClientPage(page)
    client_page.goto(therapist_client["id"])
    expect(client_page.share_form).to_be_visible()

    client_page.share_with(psychiatrist_user["email"])

    expect(client_page.shared_with_name).to_have_text(
        f"{psychiatrist_user['first_name']} {psychiatrist_user['last_name']}"
    )
    expect(client_page.shared_with_email).to_have_text(psychiatrist_user["email"])
    expect(client_page.unshare_button).to_be_visible()
    expect(client_page.share_form).not_to_be_visible()


def test_share_with_unknown_psychiatrist_shows_error(
    page: Page, therapist_user, therapist_client
):
    """The lookup step rejects unknown emails BEFORE the confirmation
    appears — that's the whole point of the two-step flow. The user
    must see the error and stay on the input form, with no confirmation
    panel and no shared-with state."""
    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])

    client_page = ClientPage(page)
    client_page.goto(therapist_client["id"])
    client_page.start_share("ghost-no-such-psych@nowhere.example")

    expect(client_page.share_error).to_contain_text("No psychiatrist registered")
    expect(client_page.share_confirm_block).not_to_be_visible()
    expect(client_page.shared_with_block).not_to_be_visible()
    expect(client_page.share_form).to_be_visible()


def test_therapist_can_unshare(
    page: Page, therapist_user, therapist_client, psychiatrist_user
):
    """After unshare, the shared-with line goes away and the share form
    returns — round-trip back to unshared state."""
    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])

    client_page = ClientPage(page)
    client_page.goto(therapist_client["id"])
    client_page.share_with(psychiatrist_user["email"])
    expect(client_page.shared_with_email).to_be_visible()

    client_page.unshare()

    expect(client_page.shared_with_block).not_to_be_visible()
    expect(client_page.share_form).to_be_visible()


def test_psychiatrist_on_shared_client_does_not_see_share_controls(
    page: Page, client_shared_with_psych
):
    """A psychiatrist viewing a client shared with them must NOT see the
    therapist-only share/unshare controls. This is the negative-visibility
    invariant — guards against accidentally exposing therapist actions."""
    psych = client_shared_with_psych["psychiatrist"]
    shared = client_shared_with_psych["client"]

    LoginPage(page).goto()
    LoginPage(page).login_as(psych["email"], psych["password"])

    client_page = ClientPage(page)
    client_page.goto(shared["id"])
    expect(client_page.header).to_have_text(
        f"{shared['first_name']} {shared['last_name']}"
    )
    expect(client_page.share_section).not_to_be_visible()
    expect(client_page.share_form).not_to_be_visible()
    expect(client_page.unshare_button).not_to_be_visible()
