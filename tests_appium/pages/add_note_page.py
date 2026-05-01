from .base_page import BasePage


class AddNotePage(BasePage):
    SCREEN = "addNote.screen"
    CONTENT = "addNote.content"
    PRIVATE_TOGGLE = "addNote.privateToggle"
    SAVE = "addNote.save"
    CANCEL = "addNote.cancel"

    def is_displayed(self) -> bool:
        return self.is_visible(self.SCREEN)

    def fill(self, content: str) -> None:
        self.type_into(self.CONTENT, content)

    def set_private(self, is_private: bool) -> None:
        # The toggle is binary; we read its 'value' attribute and tap if
        # it doesn't match the desired state. This avoids assumptions
        # about default UI state.
        toggle = self.find(self.PRIVATE_TOGGLE)
        current = toggle.get_attribute("value") in ("1", "true", "YES")
        if current != is_private:
            toggle.click()

    def save(self, content: str, is_private: bool = True) -> None:
        self.fill(content)
        # Only therapists see the toggle. If we're a psychiatrist, the
        # toggle won't exist — skip it (notes are public-only for them).
        if self.is_visible(self.PRIVATE_TOGGLE, timeout=1):
            self.set_private(is_private)
        self.tap(self.SAVE)
