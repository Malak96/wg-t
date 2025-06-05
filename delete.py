
from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult

class DeleteConfirmModal(ModalScreen):
    """Modal de confirmación para eliminar un elemento."""
    def __init__(self, message: str , on_confirm=None) -> None:
        self.message = message
        self.on_confirm = on_confirm  # Callback opcional
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.message, id="delete_message"),
            Horizontal(
                Button("Eliminar", id="btn_confirm_delete", variant="error"),
                Button("Cancelar", id="btn_cancel_delete", variant="default"),
                id="delete_buttons"
            ),
            id="delete_modal_content"
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_confirm_delete":
            if self.on_confirm:
                await self.on_confirm()
            self.app.pop_screen()
        elif event.button.id == "btn_cancel_delete":
            self.app.pop_screen()
