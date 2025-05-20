from textual.app import App, ComposeResult
from textual.widgets import (
    Button,
    Static,
    Header,
    Footer,
    Input,
    DataTable,
    TabbedContent,
    TabPane,
    Tabs,
    Label,
    ListView,
    ListItem,
)
from textual.containers import Container, Horizontal, Vertical, VerticalScroll

class SideBar(Horizontal):
    def compose(self) -> ComposeResult:
        yield Button("Nuevo", id="nuevo", variant="primary")
        yield Button("Eliminar", id="eliminar", variant="error")
        yield Static("")
        yield Button("Editar", id="editar", variant="primary")
        yield Button("Eliminar", id="eliminar2", variant="error")

class ClientList(Horizontal):
    def compose(self) -> ComposeResult:
        yield Label("Clientes", id="clientes_label")
        lv = ListView(
            ListItem(Label("Client 1")),
            ListItem(Label("Client 2")),
            ListItem(Label("Client 3")),
            id="clientes_list"
        )
        yield lv

class InstanceTable(Horizontal):
    def compose(self) -> ComposeResult:
        yield Label("Instancias", id="instancias_label")
        table = DataTable(id="instancias_table")
        table.add_columns("WG0", "WG1", "WG2", "WG3", "WG4")
        table.add_row("WG0", "WG1", "WG2", "WG3", "WG4")
        yield table

class ServerDetails(Horizontal):
    def compose(self) -> ComposeResult:
        yield Label("Detalles del Servidor", id="server_label")
        table = DataTable(id="server_table")
        table.add_columns("Campo", "Valor")
        campos = [
            "PubKey", "PrivKey", "Puerto", "Address", "DNS", "Endpoint"
        ]
        for campo in campos:
            table.add_row(campo, "")
        yield table

class EditorTabs(TabbedContent):
    def compose(self) -> ComposeResult:
        with Tabs():
            yield TabPane("Editor", id="editor_tab")
            yield TabPane("General", id="general_tab")

class MainView(Vertical):
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield SideBar()
            yield ClientList()
            yield ServerDetails()
            yield EditorTabs()
            yield InstanceTable()

class WireGuardTUI(App):
    CSS_PATH = None  # Puedes agregar un archivo CSS si quieres personalizar estilos

    def compose(self) -> ComposeResult:
        yield Header()
        yield MainView()
        yield Footer()

if __name__ == "__main__":
    app = WireGuardTUI()
    app.run()