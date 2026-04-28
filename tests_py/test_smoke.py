"""Infrastructure smoke tests — verify the basic plumbing works.

This file does NOT own any product behavior. It owns:
- The frontend serves something (homepage_loads)
- Each user fixture creates a user with the right shape and tears it
  down cleanly
- The therapist_client and client_shared_with_psych fixtures wire up
  cleanly through the conftest helpers

Domain tests live in their respective files: test_dashboard.py for
login UI, test_clients.py / test_share.py / test_notes.py for API,
test_*_ui.py for Playwright tests on each domain.
"""

from playwright.sync_api import Page, expect


def test_homepage_loads(page: Page):
    page.goto("http://localhost:5173")
    expect(page).not_to_have_title("")


def test_psychiatrist_user_fixture_creates_and_tears_down(psychiatrist_user):
    assert psychiatrist_user["email"].startswith("psych-")
    assert psychiatrist_user["role"] == "psychiatrist"
    assert "@test.sanctum.com" in psychiatrist_user["email"]


def test_therapist_user_fixture_creates_and_tears_down(therapist_user):
    assert therapist_user["email"].startswith("therapist-")
    assert therapist_user["role"] == "therapist"
    assert "@test.sanctum.com" in therapist_user["email"]


def test_therapist_user_fixture(therapist_user):
    assert therapist_user["role"] == "therapist"
    assert therapist_user["email"].startswith("therapist-")


def test_therapist_client_fixture(therapist_client):
    assert therapist_client["first_name"] == "Alice"
    assert isinstance(therapist_client["id"], int)


def test_shared_client_fixture(client_shared_with_psych):
    assert client_shared_with_psych["client"]["first_name"] == "Alice"
    assert client_shared_with_psych["psychiatrist"]["role"] == "psychiatrist"
    assert client_shared_with_psych["therapist"]["role"] == "therapist"
