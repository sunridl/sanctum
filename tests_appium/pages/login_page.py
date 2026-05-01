from .base_page import BasePage


class LoginPage(BasePage):
    SCREEN = "login.screen"
    EMAIL = "login.email"
    PASSWORD = "login.password"
    SUBMIT = "login.submit"
    ERROR = "login.error"
    SIGNUP_LINK = "login.signupLink"

    def is_displayed(self) -> bool:
        return self.is_visible(self.SCREEN)

    def login(self, email: str, password: str) -> None:
        self.type_into(self.EMAIL, email)
        self.type_into(self.PASSWORD, password)
        self.tap(self.SUBMIT)

    def error_text(self) -> str:
        return self.find(self.ERROR).text
