from .base_page import BasePage


class ShareClientPage(BasePage):
    SCREEN = "share.screen"
    EMAIL = "share.email"
    LOOKUP_BUTTON = "share.lookupButton"
    MATCH_NAME = "share.match.name"
    MATCH_EMAIL = "share.match.email"
    CONFIRM_BUTTON = "share.confirmButton"
    ERROR = "share.error"
    CANCEL = "share.cancel"

    def is_displayed(self) -> bool:
        return self.is_visible(self.SCREEN)

    def lookup(self, email: str) -> None:
        self.type_into(self.EMAIL, email)
        self.tap(self.LOOKUP_BUTTON)

    def confirm(self) -> None:
        self.tap(self.CONFIRM_BUTTON)

    def share_with(self, email: str) -> None:
        self.lookup(email)
        # Wait for the match to appear before confirming.
        self.find(self.MATCH_NAME)
        self.confirm()

    def error_text(self) -> str:
        return self.find(self.ERROR).text
