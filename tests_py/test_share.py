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


def test_double_share_with_different_psychiatrist_is_rejected(
    therapist_user, therapist_client, psychiatrist_user, second_psychiatrist_user
):
    """Sharing with a DIFFERENT valid psychiatrist while already shared
    must also be rejected — not implicitly replace the existing share.
    This is the core 'one psychiatrist at a time' invariant: switching
    requires an explicit unshare first.

    Three checks, in order of failure-mode coverage:
    1. The second request returns 409 (the most obvious assertion)
    2. shared_with still points at the FIRST psychiatrist (catches a
       bug where the backend rejects but has already overwritten state)
    3. The second psychiatrist does NOT see the client in their list
       (catches a bug where the backend rejects but has already appended
       to the second psychiatrist's list)
    """
    therapist_headers = _therapist_headers(therapist_user)

    first = httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/share",
        json={"psychiatrist_email": psychiatrist_user["email"]},
        headers=therapist_headers,
    )
    assert first.status_code == 200

    second = httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/share",
        json={"psychiatrist_email": second_psychiatrist_user["email"]},
        headers=therapist_headers,
    )
    assert second.status_code == 409

    # Invariant 2: original share is unchanged
    listing = httpx.get(f"{BASE_URL}/clients/", headers=therapist_headers).json()
    client = next(c for c in listing if c["id"] == therapist_client["id"])
    assert client["shared_with"]["email"] == psychiatrist_user["email"]

    # Invariant 3: second psychiatrist's listing must not contain the client
    second_psych_token = login_and_get_token(
        second_psychiatrist_user["email"], second_psychiatrist_user["password"]
    )
    second_psych_view = httpx.get(
        f"{BASE_URL}/clients/",
        headers={"Authorization": f"Bearer {second_psych_token}"},
    ).json()
    assert all(c["id"] != therapist_client["id"] for c in second_psych_view), (
        "second psychiatrist must not see the client — share was rejected"
    )


def test_psychiatrist_cannot_script_share_unshared_client_to_themselves(
    therapist_user, therapist_client, psychiatrist_user
):
    """A therapist creates a client and does not share it. A psychiatrist
    (or anyone) attempts a script-driven attack: directly POST to the
    share endpoint with the target email set to themselves, hoping to
    bypass the UI and self-grant access.

    The IDOR ownership check must reject this — the share endpoint
    finds the client in the *caller's* list, and the psychiatrist's
    list does not contain a client that was never shared with them.

    Three assertions for failure-mode coverage:
    1. The request returns 404 (not 200, not 403 — 404 hides existence)
    2. The therapist's view shows shared_with still null (no sneaky write)
    3. The psychiatrist's GET /clients/ view stays empty of this client
       (no leaked copy from a backend that returned 404 after mutating)
    """
    # The attacker authenticates as themselves (a real psychiatrist account)
    psych_token = login_and_get_token(
        psychiatrist_user["email"], psychiatrist_user["password"]
    )
    psych_headers = {"Authorization": f"Bearer {psych_token}"}

    # Attack: directly POST share with target=self
    attack = httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/share",
        json={"psychiatrist_email": psychiatrist_user["email"]},
        headers=psych_headers,
    )
    assert attack.status_code == 404, (
        "psychiatrist must not be able to share a client they don't own"
    )

    # Invariant: therapist's view of the client is unchanged
    therapist_headers = _therapist_headers(therapist_user)
    listing = httpx.get(f"{BASE_URL}/clients/", headers=therapist_headers).json()
    client = next(c for c in listing if c["id"] == therapist_client["id"])
    assert client["shared_with"] is None, (
        "share state must be untouched after a rejected attack"
    )

    # Invariant: psychiatrist's listing must NOT contain the client
    psych_view = httpx.get(f"{BASE_URL}/clients/", headers=psych_headers).json()
    assert all(c["id"] != therapist_client["id"] for c in psych_view), (
        "psychiatrist's view must not contain a client that was never shared"
    )


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


def test_psychiatrist_cannot_forward_share_to_another_psychiatrist(
    therapist_user, psychiatrist_user, second_psychiatrist_user, client_shared_with_psych
):
    """A psychiatrist who has been shared a client must not be able to
    re-share (forward) it to another psychiatrist. The share originator
    is the therapist; only they decide who else has access.

    Without the role check, the request would be rejected anyway — but
    by 409 (already-shared check), which leaks the information that the
    caller has access to the client. With the role check, it's 404 from
    the start: the psychiatrist learns nothing about the client's state.

    This test specifically asserts the 404, which is the post-role-check
    behavior. It would fail with 409 before the role check is added.
    """
    psych_token = login_and_get_token(
        psychiatrist_user["email"], psychiatrist_user["password"]
    )
    psych_headers = {"Authorization": f"Bearer {psych_token}"}
    therapist_headers = _therapist_headers(therapist_user)
    client_id = client_shared_with_psych["client"]["id"]

    # Attack: the first psychiatrist tries to forward-share the client
    # they have access to, to a second psychiatrist
    attack = httpx.post(
        f"{BASE_URL}/clients/{client_id}/share",
        json={"psychiatrist_email": second_psychiatrist_user["email"]},
        headers=psych_headers,
    )
    assert attack.status_code == 404, (
        "share endpoint must reject non-therapist callers with 404, not 409"
    )

    # Invariant: original share unchanged
    listing = httpx.get(f"{BASE_URL}/clients/", headers=therapist_headers).json()
    client = next(c for c in listing if c["id"] == client_id)
    assert client["shared_with"]["email"] == psychiatrist_user["email"]

    # Invariant: second psychiatrist has no access
    second_psych_token = login_and_get_token(
        second_psychiatrist_user["email"], second_psychiatrist_user["password"]
    )
    second_psych_view = httpx.get(
        f"{BASE_URL}/clients/",
        headers={"Authorization": f"Bearer {second_psych_token}"},
    ).json()
    assert all(c["id"] != client_id for c in second_psych_view)


def test_psychiatrist_cannot_unshare_their_own_share(
    therapist_user, psychiatrist_user, client_shared_with_psych
):
    """A psychiatrist who has been shared a client must NOT be able to
    revoke that share themselves via DELETE /clients/{id}/share. Unshare
    is a therapist-only action — only the share originator can dissolve
    the relationship.

    Three assertions:
    1. Returns 404 — psychiatrists shouldn't even know the endpoint
       responds for them (anti-enumeration)
    2. Therapist's view still shows shared_with set (no sneaky write)
    3. Psychiatrist still has access (rejected attack doesn't strand them)
    """
    psych_token = login_and_get_token(
        psychiatrist_user["email"], psychiatrist_user["password"]
    )
    psych_headers = {"Authorization": f"Bearer {psych_token}"}
    therapist_headers = _therapist_headers(therapist_user)
    client_id = client_shared_with_psych["client"]["id"]

    # Attack: psychiatrist hits DELETE /clients/{id}/share
    attack = httpx.delete(
        f"{BASE_URL}/clients/{client_id}/share", headers=psych_headers
    )
    assert attack.status_code == 404

    # Invariant: therapist's view still shows shared_with set to the psych
    listing = httpx.get(f"{BASE_URL}/clients/", headers=therapist_headers).json()
    client = next(c for c in listing if c["id"] == client_id)
    assert client["shared_with"] is not None, (
        "share state must not be cleared by a rejected attack"
    )
    assert client["shared_with"]["email"] == psychiatrist_user["email"]

    # Invariant: psychiatrist still has access (the partial-mutation case)
    psych_view = httpx.get(f"{BASE_URL}/clients/", headers=psych_headers).json()
    assert any(c["id"] == client_id for c in psych_view)


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
