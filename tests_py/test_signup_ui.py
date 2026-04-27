"""End-to-end UI tests for the signup flow.

These cover the user-visible journey: open signup form → fill it → land on
the dashboard already logged in. Per-field validation lives in the API tests
(test_signup.py) — duplicating it here would just be slow Playwright noise.
"""

import uuid

import httpx
from playwright.sync_api import Page, expect

from conftest import BASE_URL
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage


def _unique_email() -> str:
    return f"signup-ui-{uuid.uuid4().hex[:8]}@test.sanctum.com"


def test_new_therapist_can_sign_up_and_lands_on_dashboard(page: Page):
    email = _unique_email()
    try:
        login = LoginPage(page)
        login.goto()
        login.sign_up_as(
            email=email,
            password="secret123",
            first_name="Ada",
            last_name="Lovelace",
            role="therapist",
        )

        dashboard = DashboardPage(page)
        expect(dashboard.role_label).to_have_text("therapist")
        expect(dashboard.user_name).to_contain_text("Ada Lovelace")
        # Therapist sees the add-client form; psychiatrist would not.
        expect(page.get_by_test_id("add-client-form")).to_be_visible()
    finally:
        httpx.delete(f"{BASE_URL}/auth/users/{email}")


def test_logout_after_signup_returns_to_login_form(page: Page):
    """Regression: after signup → dashboard → logout, the user must land
    on the login form, not the signup form they came in through. The bug
    was that `mode='signup'` persisted across the auth boundary."""
    email = _unique_email()
    try:
        login = LoginPage(page)
        login.goto()
        login.sign_up_as(
            email=email,
            password="secret123",
            first_name="Ada",
            last_name="Lovelace",
            role="therapist",
        )

        dashboard = DashboardPage(page)
        expect(dashboard.role_label).to_be_visible()
        dashboard.logout()

        # Must show login form, not signup form
        expect(login.submit_button).to_be_visible()
        expect(page.get_by_test_id("signup-form")).not_to_be_visible()
    finally:
        httpx.delete(f"{BASE_URL}/auth/users/{email}")


def test_signup_with_existing_email_shows_error(page: Page, therapist_user):
    """If a user tries to sign up with an email already in use, the form
    must show a clear error and stay on the signup screen — no silent
    pass-through to the dashboard."""
    login = LoginPage(page)
    login.goto()
    login.sign_up_as(
        email=therapist_user["email"],  # already exists from the fixture
        password="secret123",
        first_name="Imposter",
        last_name="User",
        role="therapist",
    )

    expect(login.error_message).to_contain_text("already registered")
    # We must not have transitioned to the dashboard
    expect(login.signup_submit).to_be_visible()
