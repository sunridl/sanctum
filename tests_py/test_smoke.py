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

    expect(page.get_by_test_id("role-label")).to_have_text("psychiatrist")


def test_therapist_user_fixture_creates_and_tears_down(therapist_user):
    assert therapist_user["email"].startswith("therapist-")
    assert therapist_user["role"] == "therapist"
    assert "@test.sanctum.com" in therapist_user["email"]


def test_therapist_can_log_in(page, therapist_user):
    page.goto("http://localhost:5173/")

    page.get_by_placeholder("Email").fill(therapist_user["email"])
    page.get_by_placeholder("Password").fill(therapist_user["password"])
    page.get_by_role("button", name="Login").click()

    expect(page.get_by_test_id("role-label")).to_have_text("therapist")


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


def test_psychiatrist_cannot_delete_shared_client(
    therapist_user, psychiatrist_user, client_shared_with_psych
):
    """A psychiatrist who has been shared a client must not be able to
    DELETE the underlying record. Read access (via share) must not leak
    into delete access — that would let a malicious or compromised
    psychiatrist destroy the therapist's data.

    Three assertions for failure-mode coverage:
    1. Returns 404 (not 204) — IDOR-style hide
    2. Therapist's view still shows the client (not actually destroyed)
    3. Psychiatrist still has read access to the shared client (the
       failed delete must not have partially mutated state)
    """
    psych_token = login_and_get_token(
        psychiatrist_user["email"], psychiatrist_user["password"]
    )
    psych_headers = {"Authorization": f"Bearer {psych_token}"}
    therapist_token = login_and_get_token(
        therapist_user["email"], therapist_user["password"]
    )
    therapist_headers = {"Authorization": f"Bearer {therapist_token}"}
    client_id = client_shared_with_psych["client"]["id"]

    # Attack: psychiatrist hits DELETE /clients/{id}
    attack = httpx.delete(
        f"{BASE_URL}/clients/{client_id}", headers=psych_headers
    )
    assert attack.status_code == 404, (
        "psychiatrist must not be able to delete a client they only have "
        "read access to via a share"
    )

    # Invariant: therapist's client still exists
    therapist_view = httpx.get(
        f"{BASE_URL}/clients/", headers=therapist_headers
    ).json()
    assert any(c["id"] == client_id for c in therapist_view), (
        "therapist's client must not be destroyed by a rejected attack"
    )

    # Invariant: psychiatrist still has access to the shared client
    psych_view = httpx.get(f"{BASE_URL}/clients/", headers=psych_headers).json()
    assert any(c["id"] == client_id for c in psych_view), (
        "share state must be intact — partial mutation would be worse than the bug"
    )


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