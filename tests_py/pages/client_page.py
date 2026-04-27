from playwright.sync_api import Page


class ClientPage:
    """Per-client page — header, share/unshare controls, notes placeholder.

    Tests describe user intent (share, unshare, navigate back). The mechanics
    of selectors and form filling stay encapsulated here.
    """

    def __init__(self, page: Page):
        self.page = page
        self.header = page.get_by_test_id("client-header")
        self.back_link = page.get_by_test_id("back-to-dashboard")

        # Share section — only rendered for therapists
        self.share_section = page.get_by_test_id("share-section")
        self.share_form = page.get_by_test_id("share-form")
        self.share_email = page.get_by_test_id("share-email")
        self.share_submit = page.get_by_test_id("share-submit")
        self.share_error = page.get_by_test_id("share-error")

        # Shared-state UI
        self.shared_with_block = page.get_by_test_id("shared-with-block")
        self.shared_with_email = page.get_by_test_id("shared-with-email")
        self.unshare_button = page.get_by_test_id("unshare-button")

        # Notes section
        self.notes_section = page.get_by_test_id("notes-section")
        self.notes_list = page.get_by_test_id("notes-list")
        self.note_rows = page.get_by_test_id("note-row")
        self.add_note_form = page.get_by_test_id("add-note-form")
        self.add_note_content = page.get_by_test_id("add-note-content")
        self.add_note_shared_toggle = page.get_by_test_id("add-note-shared-toggle")
        self.add_note_shared_label = page.get_by_test_id("add-note-shared-label")
        self.add_note_submit = page.get_by_test_id("add-note-submit")

    @staticmethod
    def url_for(client_id: int) -> str:
        return f"http://localhost:5173/clients/{client_id}"

    def goto(self, client_id: int):
        self.page.goto(self.url_for(client_id))

    def share_with(self, psychiatrist_email: str):
        self.share_email.fill(psychiatrist_email)
        self.share_submit.click()

    def unshare(self):
        self.unshare_button.click()

    def add_note(self, content: str, *, is_private: bool = True):
        """Add a note via the form. The keyword argument speaks the data
        model's vocabulary (is_private) even though the UI's checkbox
        speaks the inverted one (shared) — that decoupling means a UI
        relabel doesn't require touching every test.

        Default is_private=True matches the new privacy-by-default UX:
        a therapist clicking submit without touching the toggle creates
        a private note. Pass is_private=False to share."""
        self.add_note_content.fill(content)
        if not is_private:
            self.add_note_shared_toggle.check()
        self.add_note_submit.click()
