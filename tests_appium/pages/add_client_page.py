from .base_page import BasePage


class AddClientPage(BasePage):
    SCREEN = "addClient.screen"
    FIRST_NAME = "addClient.firstName"
    LAST_NAME = "addClient.lastName"
    SAVE = "addClient.save"
    CANCEL = "addClient.cancel"

    def is_displayed(self) -> bool:
        return self.is_visible(self.SCREEN)

    def create(self, first_name: str, last_name: str) -> None:
        self.type_into(self.FIRST_NAME, first_name)
        self.type_into(self.LAST_NAME, last_name)
        self.tap(self.SAVE)
