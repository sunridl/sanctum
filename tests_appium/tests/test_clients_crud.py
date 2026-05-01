"""Clients CRUD tests for the therapist role.

Each test owns the client it operates on — created via the API in a
fixture, removed via the API in a finalizer. The accessibility-id of a
row is "clientsList.row.<id>", which we get from the fixture.
"""
from pages.login_page import LoginPage
from pages.clients_page import ClientsPage
from pages.add_client_page import AddClientPage
from pages.client_detail_page import ClientDetailPage
import api_helpers


def _login_as_therapist(driver):
    LoginPage(driver).login(api_helpers.THERAPIST_EMAIL, api_helpers.THERAPIST_PASSWORD)
    clients = ClientsPage(driver)
    assert clients.is_displayed()
    return clients


def test_add_client_appears_in_list(driver, unique_client_names, therapist_token):
    first_name, last_name = unique_client_names

    clients = _login_as_therapist(driver)
    clients.tap(ClientsPage.ADD_BUTTON)

    add = AddClientPage(driver)
    assert add.is_displayed()
    add.create(first_name, last_name)

    cid = api_helpers.find_client_id(therapist_token, first_name, last_name)
    assert cid is not None, "Backend should have stored the new client"
    assert clients.is_visible(ClientsPage.row(cid)), "New client row should be visible"


def test_open_client_shows_detail_screen(driver, seeded_client):
    clients = _login_as_therapist(driver)
    clients.open_client(seeded_client["id"])

    detail = ClientDetailPage(driver)
    assert detail.is_displayed()


def test_delete_client_via_detail_screen(driver, seeded_client):
    """Use the detail screen's delete button rather than swipe-to-delete —
    swipe gestures are simulator-flaky and the button path exercises the
    same backend operation."""
    clients = _login_as_therapist(driver)
    assert clients.is_visible(ClientsPage.row(seeded_client["id"]))

    clients.open_client(seeded_client["id"])
    detail = ClientDetailPage(driver)
    detail.delete_client()

    assert clients.is_displayed()
    assert not clients.is_visible(ClientsPage.row(seeded_client["id"]), timeout=3)
