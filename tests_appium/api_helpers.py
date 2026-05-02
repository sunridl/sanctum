"""Direct-to-backend helpers for test setup and cleanup.

The UI is the system-under-test; using it to *prepare* state (e.g. share
a client before the test, then unshare after) makes tests slow and
couples them. These helpers hit the FastAPI backend directly so each
test can start from a known state in milliseconds.
"""
import os
import secrets
import uuid
from typing import Optional

import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 5

# Test credentials are generated per pytest session so they never appear
# in the repo. The session-scoped fixture in conftest.py registers these
# accounts at session start and deletes them at the end. Domain is a
# fictional .io (not a reserved RFC-2606 TLD, which Pydantic's EmailStr
# rejects).
_RUN_SUFFIX = uuid.uuid4().hex[:8]
THERAPIST_EMAIL = f"test-therapist-{_RUN_SUFFIX}@sanctum-tests.io"
THERAPIST_PASSWORD = secrets.token_urlsafe(16)
PSYCH_EMAIL = f"test-psych-{_RUN_SUFFIX}@sanctum-tests.io"
PSYCH_PASSWORD = secrets.token_urlsafe(16)


def get_token(email: str, password: str) -> str:
    r = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def list_clients(token: str) -> list:
    r = requests.get(f"{BACKEND_URL}/clients/", headers=_auth(token), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def find_client_id(token: str, first_name: str, last_name: str) -> Optional[int]:
    """Return the id of the first client with matching first/last name, or None."""
    for c in list_clients(token):
        if c["first_name"] == first_name and c["last_name"] == last_name:
            return c["id"]
    return None


def create_client(first_name: str, last_name: str, token: str) -> dict:
    r = requests.post(
        f"{BACKEND_URL}/clients/",
        headers=_auth(token),
        json={"first_name": first_name, "last_name": last_name},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def unshare_client(client_id: int, token: str) -> None:
    """Idempotent — backend returns 204 even if the client wasn't shared."""
    requests.delete(
        f"{BACKEND_URL}/clients/{client_id}/share",
        headers=_auth(token),
        timeout=TIMEOUT,
    )


def delete_client(client_id: int, token: str) -> None:
    """Cascades through shares and (orphaned) notes on the backend."""
    requests.delete(
        f"{BACKEND_URL}/clients/{client_id}",
        headers=_auth(token),
        timeout=TIMEOUT,
    )


def create_note(client_id: int, content: str, is_private: bool, token: str) -> dict:
    r = requests.post(
        f"{BACKEND_URL}/clients/{client_id}/notes",
        headers=_auth(token),
        json={"content": content, "is_private": is_private},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def share_client(client_id: int, psychiatrist_email: str, token: str) -> None:
    """Idempotent helper — swallows 409 (already shared) since callers
    typically just want the end state guaranteed."""
    r = requests.post(
        f"{BACKEND_URL}/clients/{client_id}/share",
        headers=_auth(token),
        json={"psychiatrist_email": psychiatrist_email},
        timeout=TIMEOUT,
    )
    if r.status_code not in (200, 409):
        r.raise_for_status()


def delete_user(email: str, password: str) -> None:
    """Self-delete — used to clean up uniquely-emailed signup-test accounts."""
    try:
        token = get_token(email, password)
    except requests.HTTPError:
        return  # User doesn't exist; nothing to clean.
    requests.delete(
        f"{BACKEND_URL}/auth/users/{email}",
        headers=_auth(token),
        timeout=TIMEOUT,
    )
