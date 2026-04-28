"""API tests for client CRUD endpoints — GET, POST, DELETE on /clients/.

Authorization invariants for these endpoints, including delete-side IDOR
negatives. Cross-tenant IDOR negatives for share live in test_share.py;
for notes, in test_notes.py.
"""

import httpx

from conftest import BASE_URL, login_and_get_token


def _therapist_headers(therapist_user):
    token = login_and_get_token(therapist_user["email"], therapist_user["password"])
    return {"Authorization": f"Bearer {token}"}


def _psych_headers(psychiatrist_user):
    token = login_and_get_token(
        psychiatrist_user["email"], psychiatrist_user["password"]
    )
    return {"Authorization": f"Bearer {token}"}


def test_psychiatrist_cannot_create_client(psychiatrist_user):
    """The product model: only therapists own clients. Psychiatrists view
    shared copies. Allowing a psychiatrist to POST /clients/ creates a
    domain-incoherent state — a 'client' belonging to a psychiatrist
    can never be shared, viewed by anyone else, or have notes that
    reach a therapist. Even if it doesn't leak data, it's a code path
    that shouldn't exist.

    The role check returns 404 (not 403) to match the codebase's
    anti-enumeration convention.
    """
    psych_token = login_and_get_token(
        psychiatrist_user["email"], psychiatrist_user["password"]
    )
    psych_headers = {"Authorization": f"Bearer {psych_token}"}

    response = httpx.post(
        f"{BASE_URL}/clients/",
        json={"first_name": "Should", "last_name": "NotExist"},
        headers=psych_headers,
    )
    assert response.status_code == 404, (
        "psychiatrists must not be able to create clients — only therapists do"
    )

    # Invariant: the psych's client list is unchanged after the rejected attempt
    listing = httpx.get(f"{BASE_URL}/clients/", headers=psych_headers).json()
    assert all(c["first_name"] != "Should" for c in listing)


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


# ---------------------------------------------------------------------------
# Happy-path API contract — POST, DELETE, GET on /clients/.
# ---------------------------------------------------------------------------

def test_therapist_can_create_client(therapist_user):
    """Direct API contract for client creation: returns the created
    client with an integer id, the names from the request, and
    shared_with: null. Locks the response shape so a frontend rewrite
    that depends on these fields catches a backend regression."""
    headers = _therapist_headers(therapist_user)

    response = httpx.post(
        f"{BASE_URL}/clients/",
        json={"first_name": "Jordan", "last_name": "Doe"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["first_name"] == "Jordan"
    assert body["last_name"] == "Doe"
    assert body["shared_with"] is None


def test_therapist_can_delete_own_client(therapist_user, therapist_client):
    """A therapist can delete their own client. After the delete, the
    client must be gone from their listing — confirms both the 204
    response AND the side effect."""
    headers = _therapist_headers(therapist_user)

    response = httpx.delete(
        f"{BASE_URL}/clients/{therapist_client['id']}", headers=headers
    )
    assert response.status_code == 204

    listing = httpx.get(f"{BASE_URL}/clients/", headers=headers).json()
    assert all(c["id"] != therapist_client["id"] for c in listing), (
        "deleted client must not appear in the listing"
    )


def test_therapist_cannot_delete_other_therapists_client(
    therapist_client, second_therapist_user
):
    """Maria (second therapist) cannot DELETE Sarah's client. The
    caller's-list ownership check rejects with 404 — anti-enumeration
    convention. This is a different IDOR shape from the existing
    psychiatrist-attempts-delete test (different code path: the role
    check passes for Maria, so the ownership lookup is what catches it)."""
    headers = _therapist_headers(second_therapist_user)

    attack = httpx.delete(
        f"{BASE_URL}/clients/{therapist_client['id']}", headers=headers
    )
    assert attack.status_code == 404


def test_deleting_shared_client_removes_from_psychiatrist_view(
    therapist_user, psychiatrist_user, client_shared_with_psych
):
    """When a therapist deletes a client that's shared, the cascade
    must also remove it from the psychiatrist's view. Without the
    cascade, the psychiatrist would see a phantom record pointing at
    nothing."""
    therapist_headers = _therapist_headers(therapist_user)
    psych_headers = _psych_headers(psychiatrist_user)
    client_id = client_shared_with_psych["client"]["id"]

    # Sanity: psychiatrist sees the shared client before deletion
    before = httpx.get(f"{BASE_URL}/clients/", headers=psych_headers).json()
    assert any(c["id"] == client_id for c in before)

    httpx.delete(
        f"{BASE_URL}/clients/{client_id}", headers=therapist_headers
    )

    after = httpx.get(f"{BASE_URL}/clients/", headers=psych_headers).json()
    assert all(c["id"] != client_id for c in after), (
        "cascade must remove the deleted client from the psychiatrist's list"
    )


def test_get_clients_returns_owned_list_for_therapist(therapist_user):
    """Direct API contract for GET /clients/ — the therapist sees their
    own clients, each with the expected field set. After creating two
    clients, both must appear in the listing."""
    headers = _therapist_headers(therapist_user)

    a = httpx.post(
        f"{BASE_URL}/clients/",
        json={"first_name": "Alpha", "last_name": "One"},
        headers=headers,
    ).json()
    b = httpx.post(
        f"{BASE_URL}/clients/",
        json={"first_name": "Beta", "last_name": "Two"},
        headers=headers,
    ).json()

    listing = httpx.get(f"{BASE_URL}/clients/", headers=headers).json()
    ids = [c["id"] for c in listing]
    assert a["id"] in ids
    assert b["id"] in ids

    # Field contract — every entry has the expected shape
    for c in listing:
        assert isinstance(c["id"], int)
        assert "first_name" in c
        assert "last_name" in c
        assert "shared_with" in c  # may be None or the enriched object


def test_get_clients_returns_only_shared_for_psychiatrist(
    psychiatrist_user, client_shared_with_psych, second_psychiatrist_user
):
    """API-level mirror of the existing UI test. A psychiatrist's
    listing contains exactly the clients shared with them — never
    other therapists' unshared clients, never another psychiatrist's
    shared clients. Faster than the UI test and locks the contract
    independently of the frontend."""
    psych_headers = _psych_headers(psychiatrist_user)
    second_psych_headers = _psych_headers(second_psychiatrist_user)
    shared_client_id = client_shared_with_psych["client"]["id"]

    # The intended psychiatrist sees the shared client
    primary_view = httpx.get(f"{BASE_URL}/clients/", headers=psych_headers).json()
    assert any(c["id"] == shared_client_id for c in primary_view)

    # The unrelated second psychiatrist must NOT see it
    second_view = httpx.get(
        f"{BASE_URL}/clients/", headers=second_psych_headers
    ).json()
    assert all(c["id"] != shared_client_id for c in second_view)
