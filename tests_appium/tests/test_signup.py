"""Signup flow tests.

Each test creates a uniquely-emailed account so reruns don't fight over
backend state, and a finalizer cleans the account up via the backend API
to keep USERS from growing unboundedly across runs.
"""
import uuid

import pytest

from pages.login_page import LoginPage
from pages.signup_page import SignupPage
from pages.clients_page import ClientsPage
import api_helpers


@pytest.fixture
def unique_email(request):
    # NB: avoid reserved TLDs like .test/.example — email-validator (used
    # by Pydantic's EmailStr) refuses them with a 422. A normal-looking
    # fictional domain is the path of least resistance.
    email = f"test-{uuid.uuid4().hex[:8]}@sanctum-tests.io"
    password = "secret123"

    def cleanup():
        api_helpers.delete_user(email, password)

    request.addfinalizer(cleanup)
    return email, password


def test_signup_as_therapist_lands_on_clients_list(driver, unique_email):
    email, password = unique_email

    login = LoginPage(driver)
    assert login.is_displayed()
    login.tap(LoginPage.SIGNUP_LINK)

    signup = SignupPage(driver)
    assert signup.is_displayed()
    signup.signup(email, password, "Test", "Therapist", role="therapist")

    clients = ClientsPage(driver)
    assert clients.is_displayed(), "Successful signup should auto-login and show clients list"
    assert clients.has_add_button(), "New therapist should see the + button"


def test_signup_as_psychiatrist_lands_on_clients_list(driver, unique_email):
    email, password = unique_email

    LoginPage(driver).tap(LoginPage.SIGNUP_LINK)
    SignupPage(driver).signup(email, password, "Test", "Psych", role="psychiatrist")

    clients = ClientsPage(driver)
    assert clients.is_displayed()
    assert not clients.has_add_button(), "New psychiatrist should NOT see the + button"


def test_signup_with_existing_email_shows_error(driver):
    # Reuses the seeded therapist's email — the backend's /auth/signup
    # rejects duplicates with 409.
    LoginPage(driver).tap(LoginPage.SIGNUP_LINK)
    signup = SignupPage(driver)
    signup.signup(
        api_helpers.THERAPIST_EMAIL,
        "anotherpass",
        "Should",
        "Fail",
        role="therapist",
    )

    assert signup.is_displayed(), "Should remain on signup screen"
    assert "already exists" in signup.error_text().lower()
