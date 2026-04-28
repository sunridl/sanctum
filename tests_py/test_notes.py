"""API tests for the notes endpoints.

Covers role/visibility invariants on the notes endpoints AND cross-tenant
IDOR negatives — a therapist must not be able to read or write notes on
another therapist's client. Hides existence with 404 rather than 403 to
prevent ID enumeration (matches the codebase's anti-enumeration convention).
"""

import httpx
import pytest

from conftest import BASE_URL, login_and_get_token


def test_psychiatrist_cannot_create_private_note(client_shared_with_psych):
    """Private notes are therapist-only by design — the GET endpoint hides
    them from psychiatrists. The POST endpoint must reject the same role
    from creating them, otherwise the invariant can be broken via direct
    API calls (defense in depth against the UI hiding the toggle).

    The endpoint returns 404 (not 403) to match the codebase's anti-
    enumeration convention.
    """
    psych = client_shared_with_psych["psychiatrist"]
    client = client_shared_with_psych["client"]

    psych_token = login_and_get_token(psych["email"], psych["password"])
    headers = {"Authorization": f"Bearer {psych_token}"}

    response = httpx.post(
        f"{BASE_URL}/clients/{client['id']}/notes",
        json={"content": "secret psychiatrist note", "is_private": True},
        headers=headers,
    )

    assert response.status_code == 404


def test_psychiatrist_can_create_public_note(client_shared_with_psych):
    """Sanity check on the rejection above — a psychiatrist can still
    create non-private notes on a shared client. Without this, a regression
    that rejected ALL psychiatrist note creation would still pass the test
    above, which would be a false sense of safety."""
    psych = client_shared_with_psych["psychiatrist"]
    client = client_shared_with_psych["client"]

    psych_token = login_and_get_token(psych["email"], psych["password"])
    headers = {"Authorization": f"Bearer {psych_token}"}

    response = httpx.post(
        f"{BASE_URL}/clients/{client['id']}/notes",
        json={"content": "public observation", "is_private": False},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["is_private"] is False
    assert response.json()["role"] == "psychiatrist"


# ---------------------------------------------------------------------------
# Cross-tenant IDOR negatives — one therapist must not read or write notes
# on another therapist's client.
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# GET /clients/{id}/notes — happy-path API contract.
# UI behavior is tested in test_notes_ui.py; these lock the API shape
# independently so a frontend rewrite catches a backend regression.
# ---------------------------------------------------------------------------

def test_get_notes_returns_attribution_for_owner(therapist_user, therapist_client):
    """A therapist creates two notes (one private, one shared) on their
    own client and lists them via GET. The response must include both
    notes with the full attribution shape: author email, role, and the
    enriched first/last name fields."""
    token = login_and_get_token(therapist_user["email"], therapist_user["password"])
    headers = {"Authorization": f"Bearer {token}"}

    httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/notes",
        json={"content": "Private note", "is_private": True},
        headers=headers,
    )
    httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/notes",
        json={"content": "Shared note", "is_private": False},
        headers=headers,
    )

    listing = httpx.get(
        f"{BASE_URL}/clients/{therapist_client['id']}/notes", headers=headers
    )
    assert listing.status_code == 200
    notes = listing.json()
    assert len(notes) == 2

    # Field contract — attribution must be present and correct
    for n in notes:
        assert n["author"] == therapist_user["email"]
        assert n["role"] == "therapist"
        assert n["author_first_name"] == therapist_user["first_name"]
        assert n["author_last_name"] == therapist_user["last_name"]
        assert "is_private" in n


def test_get_notes_filters_private_notes_for_psychiatrist(
    therapist_user, client_shared_with_psych
):
    """API-level mirror of the UI filter test. A therapist creates a
    private and a public note on a shared client. The psychiatrist's
    GET must return only the public note. This locks the backend
    invariant directly — the UI test could pass even if the backend
    leaked private notes (e.g., if the frontend filtered them client-side)."""
    therapist_token = login_and_get_token(
        therapist_user["email"], therapist_user["password"]
    )
    therapist_headers = {"Authorization": f"Bearer {therapist_token}"}
    psych = client_shared_with_psych["psychiatrist"]
    client_id = client_shared_with_psych["client"]["id"]

    # Therapist creates one private and one public note
    httpx.post(
        f"{BASE_URL}/clients/{client_id}/notes",
        json={"content": "Private clinical impression", "is_private": True},
        headers=therapist_headers,
    )
    httpx.post(
        f"{BASE_URL}/clients/{client_id}/notes",
        json={"content": "Approved for group therapy", "is_private": False},
        headers=therapist_headers,
    )

    # Psychiatrist GETs the notes
    psych_token = login_and_get_token(psych["email"], psych["password"])
    response = httpx.get(
        f"{BASE_URL}/clients/{client_id}/notes",
        headers={"Authorization": f"Bearer {psych_token}"},
    )
    assert response.status_code == 200
    visible = response.json()

    # Must see the public note, not the private one
    contents = [n["content"] for n in visible]
    assert "Approved for group therapy" in contents
    assert "Private clinical impression" not in contents
    assert all(not n["is_private"] for n in visible)


# ---------------------------------------------------------------------------
# Input validation — empty / whitespace-only note content is meaningless
# clinically. Backend must reject (defense in depth past the UI's trim).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value,reason",
    [
        ("", "empty content"),
        ("   ", "whitespace-only content"),
    ],
)
def test_create_note_rejects_invalid_content_with_422(
    value, reason, therapist_user, therapist_client
):
    token = login_and_get_token(therapist_user["email"], therapist_user["password"])
    headers = {"Authorization": f"Bearer {token}"}

    response = httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/notes",
        json={"content": value, "is_private": True},
        headers=headers,
    )
    assert response.status_code == 422, f"expected 422 for {reason}, got {response.status_code}"
