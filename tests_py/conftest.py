import uuid
import httpx
import pytest

BASE_URL = "http://localhost:8000"


# ---------------------------------------------------------------------------
# Auth helper — not a fixture, just a utility
# ---------------------------------------------------------------------------

def login_and_get_token(email: str, password: str) -> str:
    """Log in via the backend and return a JWT."""
    response = httpx.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def psychiatrist_user():
    email = f"psych-{uuid.uuid4().hex[:8]}@test.sanctum.com"
    password = "secret123"

    response = httpx.post(
        f"{BASE_URL}/auth/users",
        json={"email": email, "password": password, "role": "psychiatrist"},
    )
    response.raise_for_status()

    user = {"email": email, "password": password, "role": "psychiatrist"}
    yield user

    httpx.delete(f"{BASE_URL}/auth/users/{email}")


@pytest.fixture
def therapist_user():
    email = f"therapist-{uuid.uuid4().hex[:8]}@test.sanctum.com"
    password = "secret123"

    response = httpx.post(
        f"{BASE_URL}/auth/users",
        json={"email": email, "password": password, "role": "therapist"},
    )
    response.raise_for_status()

    user = {"email": email, "password": password, "role": "therapist"}
    yield user

    httpx.delete(f"{BASE_URL}/auth/users/{email}")


@pytest.fixture
def second_therapist_user():
    """A second, unrelated therapist — used to verify that one therapist
    cannot access another therapist's clients or notes."""
    email = f"therapist2-{uuid.uuid4().hex[:8]}@test.sanctum.com"
    password = "secret123"

    response = httpx.post(
        f"{BASE_URL}/auth/users",
        json={"email": email, "password": password, "role": "therapist"},
    )
    response.raise_for_status()

    user = {"email": email, "password": password, "role": "therapist"}
    yield user

    httpx.delete(f"{BASE_URL}/auth/users/{email}")


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def therapist_client(therapist_user):
    """Create a client owned by the therapist. Teardown deletes via the therapist's token."""
    token = login_and_get_token(therapist_user["email"], therapist_user["password"])
    headers = {"Authorization": f"Bearer {token}"}

    response = httpx.post(
        f"{BASE_URL}/clients/",
        json={"first_name": "Alice", "last_name": "Doe"},
        headers=headers,
    )
    response.raise_for_status()
    client = response.json()

    yield client

    # Teardown: delete the client (idempotent — best-effort)
    httpx.delete(f"{BASE_URL}/clients/{client['id']}", headers=headers)


@pytest.fixture
def client_shared_with_psych(therapist_user, psychiatrist_user, therapist_client):
    """A client created by the therapist and shared with the psychiatrist."""
    token = login_and_get_token(therapist_user["email"], therapist_user["password"])
    headers = {"Authorization": f"Bearer {token}"}

    response = httpx.post(
        f"{BASE_URL}/clients/{therapist_client['id']}/share",
        json={"psychiatrist_email": psychiatrist_user["email"]},
        headers=headers,
    )
    response.raise_for_status()

    yield {
        "therapist": therapist_user,
        "psychiatrist": psychiatrist_user,
        "client": therapist_client,
    }
    # No explicit unshare teardown — when therapist_client tears down,
    # our cascading delete removes the client from every list.