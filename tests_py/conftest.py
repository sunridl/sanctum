import uuid
import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.fixture
def psychiatrist_user():
    # Arrange: create a unique user via the backend
    email = f"psych-{uuid.uuid4().hex[:8]}@test.sanctum.com"
    password = "secret123"

    response = httpx.post(
        f"{BASE_URL}/auth/users",
        json={"email": email, "password": password, "role": "psychiatrist"},
    )
    response.raise_for_status()

    user = {"email": email, "password": password, "role": "psychiatrist"}

    # Hand the user to the test
    yield user

    # Cleanup: best-effort delete, don't raise on teardown errors
    httpx.delete(f"{BASE_URL}/auth/users/{email}")