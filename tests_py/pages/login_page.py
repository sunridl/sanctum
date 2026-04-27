from playwright.sync_api import Page

class LoginPage:
    """Login + signup screen — the only place credentials are entered."""

    URL = "http://localhost:5173/"

    def __init__(self, page: Page):
        self.page = page
        self.email_input = page.get_by_test_id("login-email")
        self.password_input = page.get_by_test_id("login-password")
        self.submit_button = page.get_by_test_id("login-submit")
        self.show_signup_button = page.get_by_test_id("show-signup")
        self.show_login_button = page.get_by_test_id("show-login")
        self.error_message = page.get_by_test_id("auth-error")

        # Signup-mode controls
        self.signup_first_name = page.get_by_test_id("signup-first-name")
        self.signup_last_name = page.get_by_test_id("signup-last-name")
        self.signup_email = page.get_by_test_id("signup-email")
        self.signup_password = page.get_by_test_id("signup-password")
        self.signup_role = page.get_by_test_id("signup-role")
        self.signup_submit = page.get_by_test_id("signup-submit")

    def goto(self):
        self.page.goto(self.URL)

    def login_as(self, email: str, password: str, *, expect_success: bool = True):
        """Submit the login form. By default waits for the post-login redirect
        to /dashboard so callers can immediately navigate to deep URLs without
        racing the sessionStorage write. Pass `expect_success=False` for tests
        that assert login *fails* and stays on /."""
        self.email_input.fill(email)
        self.password_input.fill(password)
        self.submit_button.click()
        if expect_success:
            self.page.wait_for_url("**/dashboard")

    def open_signup(self):
        self.show_signup_button.click()

    def sign_up_as(self, *, email: str, password: str, first_name: str, last_name: str, role: str):
        """Open the signup form and submit it. `role` is 'therapist' or 'psychiatrist'."""
        self.open_signup()
        self.signup_first_name.fill(first_name)
        self.signup_last_name.fill(last_name)
        self.signup_email.fill(email)
        self.signup_password.fill(password)
        self.signup_role.select_option(role)
        self.signup_submit.click()
