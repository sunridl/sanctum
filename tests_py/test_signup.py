"""API tests for the public /auth/signup endpoint.

The signup endpoint is the public-facing user creation path. It must:
- accept a valid email + password + name + role and return an access token
- reject duplicates with 409 (not 422 — duplicate is a state conflict, not bad input)
- reject malformed inputs with 422 via Pydantic validation
- never echo the password back

The /auth/users endpoint is a *test-only* admin shortcut and is intentionally
not exercised here — that's what conftest fixtures use for setup.
"""

import uuid

import httpx
import pytest

from conftest import BASE_URL


def _unique_email() -> str:
    return f"signup-{uuid.uuid4().hex[:8]}@test.sanctum.com"


def _cleanup(email: str, password: str = "secret123") -> None:
    """Best-effort delete — login, then self-delete with the user's token.
    Silently absorbs failures (user may not exist, or test may have used
    a different password). Cleanup, not an assertion."""
    login = httpx.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
    )
    if login.status_code == 200:
        token = login.json()["access_token"]
        httpx.delete(
            f"{BASE_URL}/auth/users/{email}",
            headers={"Authorization": f"Bearer {token}"},
        )


def test_signup_happy_path_returns_token_and_profile():
    email = _unique_email()
    try:
        response = httpx.post(
            f"{BASE_URL}/auth/signup",
            json={
                "email": email,
                "password": "secret123",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "role": "therapist",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["access_token"]
        assert body["token_type"] == "bearer"
        assert body["role"] == "therapist"
        assert body["first_name"] == "Ada"
        assert body["last_name"] == "Lovelace"
        # Password must never come back in the response
        assert "password" not in body
    finally:
        _cleanup(email)


def test_signup_then_login_with_same_credentials():
    """A user who just signed up must be able to log in immediately —
    catches password-hashing regressions end-to-end."""
    email = _unique_email()
    password = "secret123"
    try:
        signup = httpx.post(
            f"{BASE_URL}/auth/signup",
            json={
                "email": email,
                "password": password,
                "first_name": "Grace",
                "last_name": "Hopper",
                "role": "psychiatrist",
            },
        )
        assert signup.status_code == 201

        login = httpx.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200
        assert login.json()["role"] == "psychiatrist"
    finally:
        _cleanup(email)


def test_signup_duplicate_email_returns_409():
    email = _unique_email()
    payload = {
        "email": email,
        "password": "secret123",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "role": "therapist",
    }
    try:
        first = httpx.post(f"{BASE_URL}/auth/signup", json=payload)
        assert first.status_code == 201

        second = httpx.post(f"{BASE_URL}/auth/signup", json=payload)
        assert second.status_code == 409
    finally:
        _cleanup(email)


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("email", "not-an-email", "invalid email format"),
        ("password", "short", "password under 8 chars"),
        ("first_name", "", "empty first name"),
        ("last_name", "", "empty last name"),
        ("role", "admin", "role outside {therapist, psychiatrist}"),
    ],
)
def test_signup_rejects_invalid_input_with_422(field, value, reason):
    payload = {
        "email": _unique_email(),
        "password": "secret123",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "role": "therapist",
    }
    payload[field] = value

    response = httpx.post(f"{BASE_URL}/auth/signup", json=payload)
    assert response.status_code == 422, f"expected 422 for {reason}, got {response.status_code}"
