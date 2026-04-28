"""Auth-lifecycle invariants — what happens to existing tokens AND to
other users' state when an account changes.

These cover post-signup, cross-cutting concerns:
- a deleted user's still-valid JWT must be rejected (otherwise orphaned
  data is reachable, which is the bug this file was created to prevent)
- deletion cascades to the share graph: no other user can be left
  pointing at a vanished account
"""

import uuid

import httpx

from conftest import BASE_URL, login_and_get_token


def test_deleted_users_token_returns_401_on_clients_endpoint():
    """A user is created, logs in, then is deleted. Their existing JWT
    is still cryptographically valid — but the user no longer exists in
    USERS, so any authenticated endpoint must reject the request with
    401. Without this guard, the deleted user can still see and modify
    their orphaned client list."""
    email = f"deleted-user-{uuid.uuid4().hex[:8]}@test.sanctum.com"
    password = "secret123"

    # Create the user
    create = httpx.post(
        f"{BASE_URL}/auth/users",
        json={
            "email": email,
            "password": password,
            "role": "therapist",
            "first_name": "Will",
            "last_name": "TestDeleted",
        },
    )
    assert create.status_code == 201

    # Get a token while the user exists
    token = login_and_get_token(email, password)
    headers = {"Authorization": f"Bearer {token}"}

    # Sanity check: token works before deletion
    before = httpx.get(f"{BASE_URL}/clients/", headers=headers)
    assert before.status_code == 200

    # Delete the user (self-delete via the user's own token)
    delete = httpx.delete(f"{BASE_URL}/auth/users/{email}", headers=headers)
    assert delete.status_code == 204

    # The same token must now be rejected — anything else is a bug
    after = httpx.get(f"{BASE_URL}/clients/", headers=headers)
    assert after.status_code == 401


# ---------------------------------------------------------------------------
# Account deletion authorization — only the account owner may delete
# their own account. Without this, anyone with curl could wipe arbitrary
# users.
# ---------------------------------------------------------------------------

def test_user_cannot_delete_another_users_account(
    therapist_user, psychiatrist_user
):
    """A therapist authenticates as themselves and tries to delete a
    psychiatrist's account. Must be rejected with 404, and the
    psychiatrist's account must still exist afterward.

    Returns 404 (not 403) to match the codebase's anti-enumeration
    convention — an attacker can't tell if the target email exists.
    """
    therapist_token = login_and_get_token(
        therapist_user["email"], therapist_user["password"]
    )

    attack = httpx.delete(
        f"{BASE_URL}/auth/users/{psychiatrist_user['email']}",
        headers={"Authorization": f"Bearer {therapist_token}"},
    )
    assert attack.status_code == 404, (
        "users may only delete their own accounts"
    )

    # Invariant: psychiatrist still exists — login still succeeds
    login = httpx.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": psychiatrist_user["email"],
            "password": psychiatrist_user["password"],
        },
    )
    assert login.status_code == 200, (
        "victim's account must still exist after a rejected attack"
    )


def test_unauthenticated_delete_user_is_rejected():
    """No auth header at all — the endpoint must require a token. This
    covers the original bug exactly: anyone with curl could DELETE."""
    response = httpx.delete(
        f"{BASE_URL}/auth/users/anyone@example.com",
    )
    # Either 401 (no bearer) or 403 (forbidden) is acceptable; what
    # matters is that an unauthenticated request CANNOT succeed.
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Cascade cleanup — deleting a user must not leave dangling references in
# the share graph. Without this, therapists would still see "Shared with
# deleted-psych@…" and psychiatrists would still see vanished clients.
# ---------------------------------------------------------------------------

def test_deleting_psychiatrist_clears_shared_with_on_therapists_clients(
    therapist_user, psychiatrist_user, client_shared_with_psych
):
    """A therapist shared a client with a psychiatrist. The psychiatrist
    is then deleted. The client's shared_with field must be cleared —
    otherwise the therapist's UI keeps pointing at a vanished account."""
    therapist_token = login_and_get_token(
        therapist_user["email"], therapist_user["password"]
    )
    therapist_headers = {"Authorization": f"Bearer {therapist_token}"}

    # Sanity check: shared_with is set before deletion
    listing = httpx.get(f"{BASE_URL}/clients/", headers=therapist_headers).json()
    client = next(
        c for c in listing if c["id"] == client_shared_with_psych["client"]["id"]
    )
    assert client["shared_with"]["email"] == psychiatrist_user["email"]

    # Delete the psychiatrist (self-delete via the psychiatrist's own token)
    psych_token = login_and_get_token(
        psychiatrist_user["email"], psychiatrist_user["password"]
    )
    response = httpx.delete(
        f"{BASE_URL}/auth/users/{psychiatrist_user['email']}",
        headers={"Authorization": f"Bearer {psych_token}"},
    )
    assert response.status_code == 204

    # The therapist's view must show shared_with cleared
    listing = httpx.get(f"{BASE_URL}/clients/", headers=therapist_headers).json()
    client = next(
        c for c in listing if c["id"] == client_shared_with_psych["client"]["id"]
    )
    assert client["shared_with"] is None


def test_deleting_therapist_removes_their_clients_from_psychiatrist_view(
    therapist_user, psychiatrist_user, client_shared_with_psych
):
    """The therapist owns a client and shared it with a psychiatrist.
    When the therapist is deleted, the psychiatrist must no longer see
    that client — the underlying record has no owner anymore."""
    psych_token = login_and_get_token(
        psychiatrist_user["email"], psychiatrist_user["password"]
    )
    psych_headers = {"Authorization": f"Bearer {psych_token}"}
    shared_client_id = client_shared_with_psych["client"]["id"]

    # Sanity check: psychiatrist sees the shared client before deletion
    psych_view = httpx.get(f"{BASE_URL}/clients/", headers=psych_headers).json()
    assert any(c["id"] == shared_client_id for c in psych_view)

    # Delete the therapist (self-delete via the therapist's own token)
    therapist_token = login_and_get_token(
        therapist_user["email"], therapist_user["password"]
    )
    response = httpx.delete(
        f"{BASE_URL}/auth/users/{therapist_user['email']}",
        headers={"Authorization": f"Bearer {therapist_token}"},
    )
    assert response.status_code == 204

    # The psychiatrist's view must no longer contain the orphaned client
    psych_view = httpx.get(f"{BASE_URL}/clients/", headers=psych_headers).json()
    assert all(c["id"] != shared_client_id for c in psych_view)
