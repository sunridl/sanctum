from .base_page import BasePage


class ClientsPage(BasePage):
    SCREEN = "clientsList.screen"
    EMPTY = "clientsList.empty"
    ADD_BUTTON = "clientsList.addButton"
    SETTINGS_BUTTON = "clientsList.settingsButton"

    @staticmethod
    def row(client_id: int) -> str:
        return f"clientsList.row.{client_id}"

    def is_displayed(self) -> bool:
        return self.is_visible(self.SCREEN)

    def has_add_button(self) -> bool:
        # Therapists see this; psychiatrists don't. Useful for role
        # assertions without checking the role explicitly.
        return self.is_visible(self.ADD_BUTTON, timeout=2)

    def open_settings(self) -> None:
        self.tap(self.SETTINGS_BUTTON)

    def open_client(self, client_id: int) -> None:
        self.tap(self.row(client_id))
