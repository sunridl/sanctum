"""API tests for the notes endpoints.

Covers role/visibility invariants on the notes endpoints AND cross-tenant
IDOR negatives — a therapist must not be able to read or write notes on
another therapist's client. Hides existence with 404 rather than 403 to
prevent ID enumeration (matches the codebase's anti-enumeration convention).
"""

import httpx

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
