"""Base page object: common element-finding and interaction helpers.

We standardize on AppiumBy.ACCESSIBILITY_ID for every locator, because the
SwiftUI app sets `.accessibilityIdentifier(...)` on every interactive view.
That gives us one locator strategy across the whole suite — no XPath, no
class chains, no fragility from layout changes.
"""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


DEFAULT_TIMEOUT = 15


class BasePage:
    def __init__(self, driver, timeout: int = DEFAULT_TIMEOUT):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def _locator(self, identifier: str):
        return AppiumBy.ACCESSIBILITY_ID, identifier

    def find(self, identifier: str):
        return self.wait.until(EC.presence_of_element_located(self._locator(identifier)))

    def find_all(self, identifier: str):
        # Useful for asserting "at least N rows" without binding to specific IDs.
        self.wait.until(EC.presence_of_element_located(self._locator(identifier)))
        return self.driver.find_elements(*self._locator(identifier))

    def is_visible(self, identifier: str, timeout: int = 3) -> bool:
        """Non-throwing check. Useful for branching on optional UI."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(self._locator(identifier))
            )
            return True
        except Exception:
            return False

    def tap(self, identifier: str):
        # Wait for presence rather than element_to_be_clickable: XCUITest
        # dispatches taps via the accessibility identifier, not via screen
        # coordinates, so an element that's technically off-screen (e.g.
        # below the keyboard) is still tappable. The strict "clickable"
        # predicate in Selenium would refuse and time out.
        self.find(identifier).click()

    def type_into(self, identifier: str, text: str):
        elem = self.find(identifier)
        elem.click()
        elem.clear()
        elem.send_keys(text)

    def hide_keyboard(self):
        """The iOS keyboard hides the lower portion of tall forms (signup,
        for example). Dismissing it explicitly before tapping anything
        below the last text field. No-op if no keyboard is up."""
        try:
            self.driver.execute_script("mobile: hideKeyboard")
        except Exception:
            pass
