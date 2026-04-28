"""API tests for client CRUD endpoints — POST /clients/, DELETE /clients/{id}.

Authorization invariants for these endpoints. Cross-tenant IDOR negatives
for share/notes live in test_share.py and test_smoke.py respectively.
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
