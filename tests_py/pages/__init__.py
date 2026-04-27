from playwright.sync_api import Page

class LoginPage:
    """Login screen — the only place email/password are entered."""

    URL = "http://localhost:5173/"

    def __init__(self, page: Page):
        self.page = page
        self.email_input = page.get_by_test_id("login-email")
        self.password_input = page.get_by_test_id("login-password")
        self.submit_button = page.get_by_test_id("login-submit")

    def goto(self):
        self.page.goto(self.URL)

    def login_as(self, email: str, password: str):
        self.email_input.fill(email)
        self.password_input.fill(password)
        self.submit_button.click()