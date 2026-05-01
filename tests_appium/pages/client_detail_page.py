from .base_page import BasePage


class ClientDetailPage(BasePage):
    SCREEN = "clientDetail.screen"
    NAME = "clientDetail.name"
    SHARED_WITH = "clientDetail.sharedWith"
    SHARED_WITH_NONE = "clientDetail.sharedWith.none"
    SHARE_BUTTON = "clientDetail.shareButton"
    UNSHARE_BUTTON = "clientDetail.unshareButton"
    ADD_NOTE_BUTTON = "clientDetail.addNoteButton"
    DELETE_BUTTON = "clientDetail.deleteButton"
    DELETE_CONFIRM = "clientDetail.deleteConfirm"
    DELETE_CANCEL = "clientDetail.deleteCancel"
    NOTES_EMPTY = "clientDetail.notes.empty"

    def is_displayed(self) -> bool:
        return self.is_visible(self.SCREEN)

    @staticmethod
    def note(note_id: int) -> str:
        return f"clientDetail.note.{note_id}"

    @staticmethod
    def note_private_badge(note_id: int) -> str:
        return f"note.{note_id}.privateBadge"

    def open_share_sheet(self) -> None:
        self.tap(self.SHARE_BUTTON)

    def stop_sharing(self) -> None:
        self.tap(self.UNSHARE_BUTTON)

    def open_add_note(self) -> None:
        self.tap(self.ADD_NOTE_BUTTON)

    def delete_client(self) -> None:
        self.tap(self.DELETE_BUTTON)
        self.tap(self.DELETE_CONFIRM)

    def is_shared(self) -> bool:
        return self.is_visible(self.SHARED_WITH, timeout=2)
