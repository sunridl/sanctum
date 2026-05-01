"""Share / unshare tests.

Each test uses a freshly-created client, so it always starts unshared.
The seeded_client fixture's finalizer cascades through any shares the
test created.
"""
from pages.login_page import LoginPage
from pages.clients_page import ClientsPage
from pages.client_detail_page import ClientDetailPage
from pages.share_client_page import ShareClientPage
import api_helpers


def _login_as_therapist_and_open(driver, client_id: int):
    LoginPage(driver).login(api_helpers.THERAPIST_EMAIL, api_helpers.THERAPIST_PASSWORD)
    clients = ClientsPage(driver)
    assert clients.is_displayed()
    clients.open_client(client_id)
    detail = ClientDetailPage(driver)
    assert detail.is_displayed()
    return clients, detail


def test_therapist_can_share_client_with_psychiatrist(driver, seeded_client):
    _, detail = _login_as_therapist_and_open(driver, seeded_client["id"])
    assert not detail.is_shared(), "Fresh client should start unshared"

    detail.open_share_sheet()

    share = ShareClientPage(driver)
    assert share.is_displayed()
    share.share_with(api_helpers.PSYCH_EMAIL)

    assert detail.is_displayed()
    assert detail.is_shared(), "Detail screen should now show Shared with Pat Chen"


def test_therapist_can_unshare_client(driver, seeded_client, therapist_token):
    # Pre-share via API so the test focuses on the unshare UI.
    api_helpers.share_client(seeded_client["id"], api_helpers.PSYCH_EMAIL, therapist_token)

    _, detail = _login_as_therapist_and_open(driver, seeded_client["id"])
    assert detail.is_shared()

    detail.stop_sharing()

    assert detail.is_visible(ClientDetailPage.SHARED_WITH_NONE)
    assert not detail.is_shared()


def test_share_with_unknown_email_shows_error(driver, seeded_client):
    _, detail = _login_as_therapist_and_open(driver, seeded_client["id"])
    detail.open_share_sheet()

    share = ShareClientPage(driver)
    share.lookup("nobody@nowhere.test")

    assert "No psychiatrist found" in share.error_text()


def test_psychiatrist_sees_shared_client_read_only(driver, seeded_client, therapist_token):
    """The psychiatrist's UI for a shared client must NOT include the
    Sharing section, the Delete Client button, or the add-button on the
    list — those are therapist-only."""
    api_helpers.share_client(seeded_client["id"], api_helpers.PSYCH_EMAIL, therapist_token)

    LoginPage(driver).login(api_helpers.PSYCH_EMAIL, api_helpers.PSYCH_PASSWORD)
    clients = ClientsPage(driver)
    assert clients.is_displayed()
    assert not clients.has_add_button()

    clients.open_client(seeded_client["id"])
    detail = ClientDetailPage(driver)
    assert detail.is_displayed()
    assert not detail.is_visible(ClientDetailPage.SHARE_BUTTON, timeout=2)
    assert not detail.is_visible(ClientDetailPage.UNSHARE_BUTTON, timeout=2)
    assert not detail.is_visible(ClientDetailPage.DELETE_BUTTON, timeout=2)
