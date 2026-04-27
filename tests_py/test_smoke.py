from playwright.sync_api import Page, expect
import httpx
from conftest import login_and_get_token, BASE_URL

def test_homepage_loads(page: Page):
    page.goto("http://localhost:5173")
    expect(page).not_to_have_title("")

def test_psychiatrist_user_fixture_creates_and_tears_down(psychiatrist_user):
    assert psychiatrist_user["email"].startswith("psych-")
    assert psychiatrist_user["role"] == "psychiatrist"
    assert "@test.sanctum.com" in psychiatrist_user["email"]

def test_psychiatrist_can_log_in(page, psychiatrist_user):
    page.goto("http://localhost:5173/")

    page.get_by_placeholder("Email").fill(psychiatrist_user["email"])
    page.get_by_placeholder("Password").fill(psychiatrist_user["password"])
    page.get_by_role("button", name="Login").click()

    expect(page.get_by_text("Welcome, psychiatrist")).to_be_visible()

def test_therapist_user_fixture(therapist_user):
    assert therapist_user["role"] == "therapist"
    assert therapist_user["email"].startswith("therapist-")

def test_therapist_client_fixture(therapist_client):
    assert therapist_client["first_name"] == "Alice"
    assert isinstance(therapist_client["id"], int)

def test_shared_client_fixture(client_shared_with_psych):
    assert client_shared_with_psych["client"]["first_name"] == "Alice"
    assert client_shared_with_psych["psychiatrist"]["role"] == "psychiatrist"
    assert client_shared_with_psych["therapist"]["role"] == "therapist"

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


def test_share_with_unknown_email_returns_404(therapist_user, therapist_client):
    """Sharing with an email that isn't a registered psychiatrist must fail
    cleanly with 404 — not silently succeed."""
    token = login_and_get_token(therapist_user["email"], therapist_user["password"])
    headers = {"Authorization": f"Bearer {token}"}

    response = httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/share",
        json={"psychiatrist_email": "ghost@nowhere.com"},
        headers=headers,
    )

    assert response.status_code == 404


def test_therapist_cannot_read_other_therapists_client_notes(
    therapist_user, therapist_client, second_therapist_user
):
    """Maria (second therapist) must not be able to read notes on Sarah's
    client. Endpoint hides existence with 404 to prevent object enumeration."""
    maria_token = login_and_get_token(
        second_therapist_user["email"], second_therapist_user["password"]
    )
    headers = {"Authorization": f"Bearer {maria_token}"}

    response = httpx.get(
        f"{BASE_URL}/clients/{therapist_client['id']}/notes",
        headers=headers,
    )

    assert response.status_code == 404


def test_therapist_cannot_read_other_therapists_client_notes(
    therapist_user, therapist_client, second_therapist_user
):
    """Maria (second therapist) must not be able to read notes on Sarah's
    client. Endpoint hides existence with 404 to prevent object enumeration."""
    maria_token = login_and_get_token(
        second_therapist_user["email"], second_therapist_user["password"]
    )
    headers = {"Authorization": f"Bearer {maria_token}"}

    response = httpx.get(
        f"{BASE_URL}/clients/{therapist_client['id']}/notes",
        headers=headers,
    )

    assert response.status_code == 404


def test_therapist_cannot_create_notes_on_other_therapists_client(
    therapist_user, therapist_client, second_therapist_user
):
    """Maria (second therapist) must not be able to create notes on Sarah's
    client. Endpoint hides existence with 404 to prevent object enumeration."""
    maria_token = login_and_get_token(
        second_therapist_user["email"], second_therapist_user["password"]
    )
    headers = {"Authorization": f"Bearer {maria_token}"}

    response = httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/notes",
        json={"content": "Second therapist's sneaky note", "is_private": True},
        headers=headers,
    )

    assert response.status_code == 404


def test_therapist_cannot_share_other_therapists_client(
    therapist_user, therapist_client, second_therapist_user, psychiatrist_user
):
    """Maria must not be able to share Sarah's client, even with a real
    psychiatrist. Endpoint must hide existence with 404."""
    maria_token = login_and_get_token(
        second_therapist_user["email"], second_therapist_user["password"]
    )
    headers = {"Authorization": f"Bearer {maria_token}"}

    response = httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/share",
        json={"psychiatrist_email": psychiatrist_user["email"]},
        headers=headers,
    )

    assert response.status_code == 404