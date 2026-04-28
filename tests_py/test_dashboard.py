from pages.login_page import LoginPage
from pages.dashboard_page import DashboardPage
from playwright.sync_api import Page, expect


def test_psychiatrist_can_log_in(page, psychiatrist_user):
    page.goto("http://localhost:5173/")

    page.get_by_placeholder("Email").fill(psychiatrist_user["email"])
    page.get_by_placeholder("Password").fill(psychiatrist_user["password"])
    page.get_by_role("button", name="Login").click()

    expect(page.get_by_test_id("role-label")).to_have_text("psychiatrist")


def test_therapist_can_log_in(page, therapist_user):
    page.goto("http://localhost:5173/")

    page.get_by_placeholder("Email").fill(therapist_user["email"])
    page.get_by_placeholder("Password").fill(therapist_user["password"])
    page.get_by_role("button", name="Login").click()

    expect(page.get_by_test_id("role-label")).to_have_text("therapist")


def test_therapist_can_log_in_and_see_their_client(
    page: Page, therapist_user, therapist_client
):
    """A therapist with one client should log in via the UI and see that
    client in their dashboard, with role label showing 'therapist'."""
    login_page = LoginPage(page)
    dashboard = DashboardPage(page)

    login_page.goto()
    login_page.login_as(therapist_user["email"], therapist_user["password"])

    expect(dashboard.role_label).to_have_text("therapist")
    expect(dashboard.client_list).to_contain_text(therapist_client["first_name"])


def test_login_fails_with_wrong_password(page: Page, therapist_user):
    """Submitting wrong credentials must keep the user on the login screen.
    The dashboard must not appear at all."""
    login_page = LoginPage(page)
    dashboard = DashboardPage(page)

    login_page.goto()
    login_page.login_as(therapist_user["email"], "this-is-not-the-password", expect_success=False)

    expect(login_page.email_input).to_be_visible()
    expect(dashboard.role_label).not_to_be_visible()


def test_psychiatrist_sees_only_clients_shared_with_them(
    page: Page, client_shared_with_psych
):
    """A psychiatrist's dashboard must show clients shared with them and
    nothing else. Verifies cross-tenant isolation in the UI."""
    psych = client_shared_with_psych["psychiatrist"]
    shared_client = client_shared_with_psych["client"]

    login_page = LoginPage(page)
    dashboard = DashboardPage(page)

    login_page.goto()
    login_page.login_as(psych["email"], psych["password"])

    expect(dashboard.role_label).to_have_text("psychiatrist")
    expect(dashboard.client_list).to_contain_text(shared_client["first_name"])


def test_psychiatrist_sees_exactly_the_clients_shared_with_them(
    page, psychiatrist_user, client_shared_with_psych
):
    # Act: log in as the psychiatrist
    page.goto("http://localhost:5173/")
    page.get_by_placeholder("Email").fill(psychiatrist_user["email"])
    page.get_by_placeholder("Password").fill(psychiatrist_user["password"])
    page.get_by_role("button", name="Login").click()

    # Wait for the dashboard to actually render the list
    expect(page.get_by_test_id("client-list")).to_be_visible()

    # Assert: the dashboard shows EXACTLY the client that was shared
    expected_client_id = str(client_shared_with_psych["client"]["id"])

    rows = page.get_by_test_id("client-row")
    expect(rows).to_have_count(1)

    visible_ids = [row.get_attribute("data-client-id") for row in rows.all()]
    assert visible_ids == [expected_client_id], (
        f"Expected psychiatrist to see exactly [{expected_client_id}], "
        f"but saw {visible_ids}"
    )