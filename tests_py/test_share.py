"""API tests for the share / unshare flow.

Covers the server-side invariants that the new client page relies on:
- a client carries `shared_with` (None or one psychiatrist email)
- POST /clients/{id}/share sets it
- a second POST when already shared is rejected (409) — defense in depth
  against the UI showing the share form when state already exists
- DELETE /clients/{id}/share clears the state and removes the client from
  the psychiatrist's list, and is idempotent (204 even if not shared)

The cross-tenant IDOR negative case is already covered in test_smoke.py.
"""

import httpx

from conftest import BASE_URL, login_and_get_token


def _therapist_headers(therapist_user):
    token = login_and_get_token(therapist_user["email"], therapist_user["password"])
    return {"Authorization": f"Bearer {token}"}


def test_new_client_starts_with_no_share(therapist_user, therapist_client):
    headers = _therapist_headers(therapist_user)
    response = httpx.get(f"{BASE_URL}/clients/", headers=headers)
    assert response.status_code == 200
    client = next(c for c in response.json() if c["id"] == therapist_client["id"])
    assert client["shared_with"] is None


def test_share_sets_shared_with_field(therapist_user, therapist_client, psychiatrist_user):
    headers = _therapist_headers(therapist_user)
    response = httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/share",
        json={"psychiatrist_email": psychiatrist_user["email"]},
        headers=headers,
    )
    assert response.status_code == 200

    listing = httpx.get(f"{BASE_URL}/clients/", headers=headers).json()
    client = next(c for c in listing if c["id"] == therapist_client["id"])
    # shared_with is now an object: {email, first_name, last_name}
    assert client["shared_with"]["email"] == psychiatrist_user["email"]
    assert client["shared_with"]["first_name"] == psychiatrist_user["first_name"]
    assert client["shared_with"]["last_name"] == psychiatrist_user["last_name"]


def test_share_when_already_shared_returns_409(
    therapist_user, therapist_client, psychiatrist_user
):
    """The client model only allows one psychiatrist at a time. The UI
    hides the share form when a share exists; the 409 here is the
    backend's invariant guard."""
    headers = _therapist_headers(therapist_user)
    body = {"psychiatrist_email": psychiatrist_user["email"]}

    first = httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/share", json=body, headers=headers
    )
    assert first.status_code == 200

    second = httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/share", json=body, headers=headers
    )
    assert second.status_code == 409


def test_unshare_clears_field_and_removes_from_psychiatrist_list(
    therapist_user, therapist_client, psychiatrist_user
):
    therapist_headers = _therapist_headers(therapist_user)
    psych_token = login_and_get_token(
        psychiatrist_user["email"], psychiatrist_user["password"]
    )
    psych_headers = {"Authorization": f"Bearer {psych_token}"}

    # Set up: share, then verify psychiatrist sees it
    httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/share",
        json={"psychiatrist_email": psychiatrist_user["email"]},
        headers=therapist_headers,
    )
    psych_view = httpx.get(f"{BASE_URL}/clients/", headers=psych_headers).json()
    assert any(c["id"] == therapist_client["id"] for c in psych_view)

    # Act: unshare
    response = httpx.delete(
        f"{BASE_URL}/clients/{therapist_client['id']}/share", headers=therapist_headers
    )
    assert response.status_code == 204

    # Verify: therapist's view shows shared_with cleared
    listing = httpx.get(f"{BASE_URL}/clients/", headers=therapist_headers).json()
    client = next(c for c in listing if c["id"] == therapist_client["id"])
    assert client["shared_with"] is None

    # Verify: psychiatrist no longer sees the client
    psych_view = httpx.get(f"{BASE_URL}/clients/", headers=psych_headers).json()
    assert all(c["id"] != therapist_client["id"] for c in psych_view)


def test_unshare_is_idempotent_when_not_shared(therapist_user, therapist_client):
    """An unshare on a client that isn't shared is a no-op, not an error.
    Standard REST idempotency for DELETE."""
    headers = _therapist_headers(therapist_user)
    response = httpx.delete(
        f"{BASE_URL}/clients/{therapist_client['id']}/share", headers=headers
    )
    assert response.status_code == 204


def test_unshare_on_other_therapists_client_returns_404(
    therapist_user, therapist_client, second_therapist_user
):
    """A second therapist must not be able to unshare someone else's client.
    The endpoint hides existence with 404 to prevent ID enumeration."""
    maria_token = login_and_get_token(
        second_therapist_user["email"], second_therapist_user["password"]
    )
    headers = {"Authorization": f"Bearer {maria_token}"}
    response = httpx.delete(
        f"{BASE_URL}/clients/{therapist_client['id']}/share", headers=headers
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Psychiatrist lookup — used by the share-confirmation step
# ---------------------------------------------------------------------------

def test_lookup_psychiatrist_returns_name_for_therapist(
    therapist_user, psychiatrist_user
):
    """A therapist looking up a real psychiatrist must get their name back —
    that's what the confirmation dialog renders. Without this, a typo'd
    email shows the same confirmation as a correct one."""
    headers = _therapist_headers(therapist_user)
    response = httpx.get(
        f"{BASE_URL}/auth/psychiatrists/{psychiatrist_user['email']}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == psychiatrist_user["email"]
    assert body["first_name"] == psychiatrist_user["first_name"]
    assert body["last_name"] == psychiatrist_user["last_name"]


def test_lookup_unknown_email_returns_404(therapist_user):
    headers = _therapist_headers(therapist_user)
    response = httpx.get(
        f"{BASE_URL}/auth/psychiatrists/ghost-no-such-user@nowhere.example",
        headers=headers,
    )
    assert response.status_code == 404


def test_lookup_therapist_email_returns_404(therapist_user, second_therapist_user):
    """Looking up another therapist must return 404 — same shape as an
    unknown email. This prevents using the lookup endpoint to harvest
    therapist accounts by probing role membership."""
    headers = _therapist_headers(therapist_user)
    response = httpx.get(
        f"{BASE_URL}/auth/psychiatrists/{second_therapist_user['email']}",
        headers=headers,
    )
    assert response.status_code == 404


def test_lookup_as_psychiatrist_returns_404(psychiatrist_user):
    """A psychiatrist hitting the lookup endpoint gets 404 — they don't
    need it (only therapists share clients), and 404 keeps the role-check
    indistinguishable from a normal not-found response."""
    psych_token = login_and_get_token(
        psychiatrist_user["email"], psychiatrist_user["password"]
    )
    headers = {"Authorization": f"Bearer {psych_token}"}
    response = httpx.get(
        f"{BASE_URL}/auth/psychiatrists/{psychiatrist_user['email']}",
        headers=headers,
    )
    assert response.status_code == 404


def test_lookup_unauthenticated_returns_401():
    response = httpx.get(
        f"{BASE_URL}/auth/psychiatrists/anyone@example.com",
    )
    # No bearer token — auth dependency rejects before role check
    assert response.status_code in (401, 403)
