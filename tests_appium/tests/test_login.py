"""End-to-end login tests against the running iOS app + FastAPI backend.

Each test starts from a clean state thanks to -resetState YES in the
driver fixture, so order is irrelevant.
"""
from pages.login_page import LoginPage
from pages.clients_page import ClientsPage


def test_login_screen_is_visible_on_launch(driver):
    login = LoginPage(driver)
    assert login.is_displayed()


def test_therapist_can_log_in_and_sees_clients_list(driver):
    LoginPage(driver).login("therapist@sanctum.com", "secret123")

    clients = ClientsPage(driver)
    assert clients.is_displayed(), "Therapist should land on the clients list"
    assert clients.has_add_button(), "Therapist UI must include the + button"


def test_psychiatrist_lands_on_clients_list_without_add_button(driver):
    LoginPage(driver).login("psych@sanctum.com", "secret123")

    clients = ClientsPage(driver)
    assert clients.is_displayed()
    assert not clients.has_add_button(), "Psychiatrist UI must not show the + button"


def test_login_with_bad_password_shows_error(driver):
    login = LoginPage(driver)
    login.login("therapist@sanctum.com", "wrongpassword")

    assert login.is_displayed(), "Should still be on the login screen"
    assert "Invalid credentials" in login.error_text()
