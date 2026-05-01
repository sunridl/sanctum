from .base_page import BasePage


class SignupPage(BasePage):
    SCREEN = "signup.screen"
    EMAIL = "signup.email"
    PASSWORD = "signup.password"
    FIRST_NAME = "signup.firstName"
    LAST_NAME = "signup.lastName"
    ROLE_THERAPIST = "signup.role.therapist"
    ROLE_PSYCHIATRIST = "signup.role.psychiatrist"
    SUBMIT = "signup.submit"
    ERROR = "signup.error"

    def is_displayed(self) -> bool:
        return self.is_visible(self.SCREEN)

    def fill(self, email: str, password: str, first_name: str, last_name: str) -> None:
        self.type_into(self.EMAIL, email)
        self.type_into(self.PASSWORD, password)
        self.type_into(self.FIRST_NAME, first_name)
        self.type_into(self.LAST_NAME, last_name)

    def select_role(self, role: str) -> None:
        if role == "therapist":
            self.tap(self.ROLE_THERAPIST)
        elif role == "psychiatrist":
            self.tap(self.ROLE_PSYCHIATRIST)
        else:
            raise ValueError(f"Unknown role: {role}")

    def submit(self) -> None:
        # The submit button sits below the keyboard's footprint after
        # filling all four fields. Dismiss before tapping or the click
        # lands on the keyboard.
        self.hide_keyboard()
        self.tap(self.SUBMIT)

    def signup(self, email: str, password: str, first_name: str, last_name: str, role: str) -> None:
        self.fill(email, password, first_name, last_name)
        self.hide_keyboard()
        self.select_role(role)
        self.submit()

    def error_text(self) -> str:
        return self.find(self.ERROR).text
