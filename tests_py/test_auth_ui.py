"""End-to-end UI tests for auth-lifecycle scenarios.

These cover what the user sees when their account state changes mid-session,
not the happy-path login/signup flows (those live in test_dashboard.py and
test_signup_ui.py).
"""

import httpx
from playwright.sync_api import Page, expect

from conftest import BASE_URL, login_and_get_token
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage


def test_dashboard_shows_deletion_message_when_user_was_deleted(
    page: Page, therapist_user
):
    """A therapist logs in, then their account is deleted while they're
    using the app. On the next dashboard load (page reload, navigation
    back from /clients/:id, etc.), the dashboard must show a clear
    'Your user was deleted' message rather than the client list.

    Without the backend 401 + frontend message, the deleted user would
    see their orphaned client list as if nothing had changed.
    """
    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])

    # Sanity check: the normal dashboard rendered before the deletion
    dashboard = DashboardPage(page)
    expect(dashboard.role_label).to_have_text("therapist")

    # Delete the account out from under the live session (self-delete)
    therapist_token = login_and_get_token(
        therapist_user["email"], therapist_user["password"]
    )
    response = httpx.delete(
        f"{BASE_URL}/auth/users/{therapist_user['email']}",
        headers={"Authorization": f"Bearer {therapist_token}"},
    )
    assert response.status_code == 204

    # Reload triggers a fresh loadClients() — which now returns 401
    page.reload()

    # The deletion message must replace the normal dashboard content
    expect(page.get_by_test_id("user-deleted-block")).to_be_visible()
    expect(page.get_by_test_id("user-deleted-message")).to_contain_text(
        "Your user was deleted"
    )
    # Normal dashboard content must NOT render alongside the deletion message
    expect(page.get_by_test_id("client-list")).not_to_be_visible()
    expect(page.get_by_test_id("add-client-form")).not_to_be_visible()


def test_signup_again_button_clears_session_and_returns_to_login(
    page: Page, therapist_user
):
    """Clicking 'Sign up again' from the deletion banner must clear the
    stored session and return the user to the login page — the next
    fresh load shouldn't drop them back into the deleted-user state."""
    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])

    therapist_token = login_and_get_token(
        therapist_user["email"], therapist_user["password"]
    )
    httpx.delete(
        f"{BASE_URL}/auth/users/{therapist_user['email']}",
        headers={"Authorization": f"Bearer {therapist_token}"},
    )
    page.reload()

    expect(page.get_by_test_id("user-deleted-block")).to_be_visible()
    page.get_by_test_id("user-deleted-signup-button").click()

    # Landed on /, login form is visible, no deletion banner
    expect(page).to_have_url("http://localhost:5173/")
    login = LoginPage(page)
    expect(login.email_input).to_be_visible()
    expect(page.get_by_test_id("user-deleted-block")).not_to_be_visible()
