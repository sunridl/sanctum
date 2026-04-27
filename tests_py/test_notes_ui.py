"""End-to-end UI tests for the notes section on the client page.

Privacy-by-default model:
- a therapist who submits without touching the toggle creates a PRIVATE note
- the "shared" toggle is the explicit opt-in to make a note visible to the psychiatrist
- the "shared" badge is shown to therapists only — it flags the exception, not the default

These tests focus on the user-visible mechanics. Per-input validation and
the backend's "psych can't create private" rule are covered in test_notes.py.
"""

from playwright.sync_api import Page, expect

from pages.client_page import ClientPage
from pages.login_page import LoginPage


def test_therapist_creates_private_note_by_default(
    page: Page, therapist_user, therapist_client
):
    """A therapist who fills the textarea and hits submit — without
    touching the shared toggle — must create a PRIVATE note. Privacy-
    by-default is the safety guarantee; this test locks it in.

    A private note shows no 'shared' badge."""
    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])

    client_page = ClientPage(page)
    client_page.goto(therapist_client["id"])
    client_page.add_note("Initial intake — patient seems anxious.")

    expect(client_page.note_rows).to_have_count(1)
    row = client_page.note_rows.first
    expect(row).to_contain_text("Initial intake")
    expect(row.get_by_test_id("note-author-name")).to_have_text(
        f"{therapist_user['first_name']} {therapist_user['last_name']}"
    )
    expect(row.get_by_test_id("note-role")).to_have_text("therapist")
    expect(row.get_by_test_id("note-author-email")).to_have_text(therapist_user["email"])
    expect(row.get_by_test_id("note-shared-badge")).to_have_count(0)


def test_therapist_creates_shared_note_with_badge(
    page: Page, therapist_user, therapist_client
):
    """Checking the shared toggle must produce a note marked with the
    'shared' badge — the visual signal to the therapist that this note
    is visible to the psychiatrist."""
    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])

    client_page = ClientPage(page)
    client_page.goto(therapist_client["id"])
    client_page.add_note("Group therapy approved.", is_private=False)

    row = client_page.note_rows.first
    expect(row.get_by_test_id("note-shared-badge")).to_be_visible()


def test_psychiatrist_does_not_see_private_notes(
    page: Page, therapist_user, client_shared_with_psych
):
    """The therapist seeds one shared and one private note. The
    psychiatrist must see ONLY the shared one. Backend filter mirrored
    end-to-end in the UI."""
    psych = client_shared_with_psych["psychiatrist"]
    shared_client = client_shared_with_psych["client"]

    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])
    client_page = ClientPage(page)
    client_page.goto(shared_client["id"])
    client_page.add_note("Group session approved.", is_private=False)
    expect(client_page.note_rows).to_have_count(1)
    client_page.add_note("Suspect underlying trauma.")  # default = private
    expect(client_page.note_rows).to_have_count(2)

    # Switch to the psychiatrist
    page.context.clear_cookies()
    page.evaluate("sessionStorage.clear()")
    LoginPage(page).goto()
    LoginPage(page).login_as(psych["email"], psych["password"])
    client_page.goto(shared_client["id"])

    expect(client_page.note_rows).to_have_count(1)
    expect(client_page.note_rows.first).to_contain_text("Group session approved")


def test_psychiatrist_does_not_see_shared_toggle(
    page: Page, client_shared_with_psych
):
    """The shared toggle is therapist-only — psychiatrists can only
    create non-private notes (enforced by the backend 404), and the UI
    reflects that by hiding the toggle entirely."""
    psych = client_shared_with_psych["psychiatrist"]
    shared_client = client_shared_with_psych["client"]

    LoginPage(page).goto()
    LoginPage(page).login_as(psych["email"], psych["password"])

    client_page = ClientPage(page)
    client_page.goto(shared_client["id"])
    expect(client_page.add_note_form).to_be_visible()
    expect(client_page.add_note_shared_label).not_to_be_visible()
    expect(client_page.add_note_shared_toggle).not_to_be_visible()


def test_psychiatrist_does_not_see_shared_badge(
    page: Page, therapist_user, client_shared_with_psych
):
    """The 'shared' badge is therapist-only context. For a psychiatrist
    every note they see is shared by definition — a badge would be
    redundant noise. This test guards against accidentally rendering it."""
    psych = client_shared_with_psych["psychiatrist"]
    shared_client = client_shared_with_psych["client"]

    LoginPage(page).goto()
    LoginPage(page).login_as(therapist_user["email"], therapist_user["password"])
    client_page = ClientPage(page)
    client_page.goto(shared_client["id"])
    client_page.add_note("Visible to psych.", is_private=False)

    page.context.clear_cookies()
    page.evaluate("sessionStorage.clear()")
    LoginPage(page).goto()
    LoginPage(page).login_as(psych["email"], psych["password"])
    client_page.goto(shared_client["id"])

    expect(client_page.note_rows).to_have_count(1)
    expect(page.get_by_test_id("note-shared-badge")).to_have_count(0)
