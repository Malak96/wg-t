
from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult

class ConfirmModal(ModalScreen):
    def __init__(self, message: str , on_confirm=None) -> None:
        self.message = message
        self.on_confirm = on_confirm  # Callback opcional
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.message, id="message"),
            Horizontal(
                Button("Eliminar", id="btn_confirm", variant="error"),
                Button("Cancelar", id="btn_cancel", variant="default"),
                id="delete_buttons"
            ),
            id="confirm_msg"
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_confirm":
            if self.on_confirm:
                await self.on_confirm()
            self.app.pop_screen()
        elif event.button.id == "btn_cancel":
            self.app.pop_screen()
