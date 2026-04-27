from playwright.sync_api import Page

class DashboardPage:
    """Authenticated home view — client list, role badge, logout."""

    def __init__(self, page: Page):
        self.page = page
        self.role_label = page.get_by_test_id("role-label")
        self.client_list = page.get_by_test_id("client-list")
        self.logout_button = page.get_by_role("button", name="Logout")

    def logout(self):
        self.logout_button.click()