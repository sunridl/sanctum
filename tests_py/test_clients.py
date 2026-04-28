"""API tests for client CRUD endpoints — POST /clients/, DELETE /clients/{id}.

Authorization invariants for these endpoints, including delete-side IDOR
negatives. Cross-tenant IDOR negatives for share live in test_share.py;
for notes, in test_notes.py.
"""

import httpx

from conftest import BASE_URL, login_and_get_token


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
