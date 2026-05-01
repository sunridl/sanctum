"""Notes tests.

The therapist creates public + private notes via the UI; a separate test
asserts the privacy gate by logging in as the psychiatrist who has access
to the same client and verifying private notes are filtered out.
"""
import uuid

from pages.login_page import LoginPage
from pages.clients_page import ClientsPage
from pages.client_detail_page import ClientDetailPage
from pages.add_note_page import AddNotePage
import api_helpers


def _login_and_open_client(driver, email: str, password: str, client_id: int):
    LoginPage(driver).login(email, password)
    clients = ClientsPage(driver)
    assert clients.is_displayed()
    clients.open_client(client_id)
    detail = ClientDetailPage(driver)
    assert detail.is_displayed()
    return detail


def test_therapist_can_add_a_public_note(driver, seeded_client):
    detail = _login_and_open_client(
        driver,
        api_helpers.THERAPIST_EMAIL,
        api_helpers.THERAPIST_PASSWORD,
        seeded_client["id"],
    )
    detail.open_add_note()

    note_text = f"Public note {uuid.uuid4().hex[:6]}"
    add = AddNotePage(driver)
    assert add.is_displayed()
    add.save(note_text, is_private=False)

    assert detail.is_displayed()
    assert note_text in detail.driver.page_source


def test_therapist_can_add_a_private_note(driver, seeded_client):
    detail = _login_and_open_client(
        driver,
        api_helpers.THERAPIST_EMAIL,
        api_helpers.THERAPIST_PASSWORD,
        seeded_client["id"],
    )
    detail.open_add_note()

    note_text = f"Private note {uuid.uuid4().hex[:6]}"
    add = AddNotePage(driver)
    add.save(note_text, is_private=True)

    assert detail.is_displayed()
    assert note_text in detail.driver.page_source


def test_psychiatrist_does_not_see_private_notes(driver, seeded_client, therapist_token):
    """End-to-end privacy assertion: share the client with the psychiatrist
    via the API, create one private and one public note, then log in as
    the psychiatrist and verify only the public note is visible."""
    api_helpers.share_client(seeded_client["id"], api_helpers.PSYCH_EMAIL, therapist_token)

    public_marker = f"PUB-{uuid.uuid4().hex[:8]}"
    private_marker = f"PRIV-{uuid.uuid4().hex[:8]}"
    api_helpers.create_note(seeded_client["id"], public_marker, is_private=False, token=therapist_token)
    api_helpers.create_note(seeded_client["id"], private_marker, is_private=True, token=therapist_token)

    detail = _login_and_open_client(
        driver,
        api_helpers.PSYCH_EMAIL,
        api_helpers.PSYCH_PASSWORD,
        seeded_client["id"],
    )
    source = detail.driver.page_source
    assert public_marker in source, "Psychiatrist must see public notes"
    assert private_marker not in source, "Psychiatrist must NOT see private notes"
