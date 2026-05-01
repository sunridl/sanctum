from .base_page import BasePage


class SettingsPage(BasePage):
    SCREEN = "settings.screen"
    DONE = "settings.done"
    LOGOUT = "settings.logout"
    DELETE_ACCOUNT = "settings.deleteAccount"
    DELETE_ACCOUNT_CONFIRM = "settings.deleteAccount.confirm"
    DELETE_ACCOUNT_CANCEL = "settings.deleteAccount.cancel"
    PROFILE_EMAIL = "settings.profile.email"
    PROFILE_ROLE = "settings.profile.role"

    def is_displayed(self) -> bool:
        return self.is_visible(self.SCREEN)

    def logout(self) -> None:
        self.tap(self.LOGOUT)

    def delete_account(self) -> None:
        self.tap(self.DELETE_ACCOUNT)
        self.tap(self.DELETE_ACCOUNT_CONFIRM)

    def email(self) -> str:
        return self.find(self.PROFILE_EMAIL).text

    def role(self) -> str:
        return self.find(self.PROFILE_ROLE).text
