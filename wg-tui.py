from textual import containers, on 
# Importar la clase principal de la aplicación y el tipo ComposeResult
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
# Importar los contenedores para organizar el layout
from textual.containers import Container, Vertical, Horizontal

# Importar los widgets básicos para la UI
from textual.widgets import Button, ListView, ListItem, Label, Input, Static, DataTable, Select, Link

import json
from textual.widget import Widget
from textual.binding import Binding
file_path = "wg_data.json"


  
class TerminalUI(App):
    
    ENABLE_COMMAND_PALETTE = False
    BORDER_TITLE = "WG-TUI - A simple terminal interface for WireGuard"
    """A Textual app for managing instances and clients."""

    # Define the CSS for the app
    CSS_PATH = "styles.css"

    async def refresh_instances_list(self):
        
        """Actualiza el ListView de instancias según wg_data."""
        selct_instance = self.query_one("#select_instance", Select)
        selct_instance.clear()
        list_cl = []
        # Asegúrate de iterar sobre los servidores, no sobre el diccionario raíz
        for name, instance in self.wg_data["servres"].items():
            # Añadir opciones al Select
            list_cl.append((name, instance["name"]))
            
    
        # Añadir opciones al Select 
        selct_instance.set_options(list_cl)

    async def on_mount(self) -> None:
        """Carga datos y refresca la lista al iniciar."""
        self.load_wg_data_from_json("wg_data.json")
        await self.refresh_instances_list()
        # Configura el DataTable para selección de fila completa
        clients_table = self.query_one("#clients_table", DataTable)
        clients_table.cursor_type = "row"
        clients_table.zebra_stripes = True

    def load_wg_data_from_json(self, file_path):
        """Carga wg_data desde un archivo JSON."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Si tu JSON tiene la clave "servres", usa esa parte
            self.wg_data = data.get("servrs", data)



    @on(Select.Changed, "#select_instance")
    def slect_client(self, event: Select.Changed) -> None:
        """Actualiza el DataTable de clientes al seleccionar un cliente."""
        selected_client = event.value
        id_name = selected_client
        instance = self.wg_data["servres"][id_name]

        self.query_one("#input_pubkey", Label).update(instance.get("publicKey", ""))
        self.query_one("#input_privkey", Label).update(instance.get("privateKey", ""))
        self.query_one("#input_address", Label).update(instance.get("address", ""))
        self.query_one("#input_port", Label).update(str(instance.get("port", "")))
        self.query_one("#input_dns", Label).update(instance.get("dns", ""))
        self.query_one("#input_endpoint", Label).update(instance.get("endpoint", ""))

        # Actualiza el DataTable de clientes
        clients_table = self.query_one("#clients_table", DataTable)
        clients_table.clear()
        # Definir columnas si no existen
        if not clients_table.columns:
            clients_table.add_columns("Nombre", "Dirección", "Clave Pública", "AllowedIPs", "Habilitado")
        # Cargar clientes del servidor seleccionado
        clients_dict = instance.get("clients", {})
        for client_id, client in clients_dict.items():
            clients_table.add_row(
                client.get("name", ""),
                client.get("address", ""),
                client.get("publicKey", ""),
                client.get("allowedIPs", ""),
                "Sí" if client.get("enabled", False) else "No"
            )
    info = Static("by malak96", classes="header-box")
    def compose(self) -> ComposeResult:
        
        self.app.theme = "nord"
        """Compose the layout of the app."""
        xx = [("First", 1), ("Second", 2)]
        with containers.Container(classes="main-container"):
            yield Static(self.BORDER_TITLE, classes="header-box")
            yield self.info
            yield Horizontal(
                Vertical(
                    Label("Instancias"),
                    ListView(
                        id="list_instances",
                        classes="list-view"
                    ),
                    Horizontal(
                        Button("Nuevo", id="btn_edit_client", classes="list-btn"),
                        Button("Eliminar", id="btn_delete_client", classes="list-btn",variant="error"),
                        classes="button-row"
                    ),
                    classes="left-panel"
                ),      
                Vertical(
                    Select([],
                        id="select_instance",
                        prompt="Selecciona una Instancia",
                    ),
                    Static(),
                    Label("Detalles"),
                    Vertical(
                        Horizontal(Label("PubKey:", classes="field-label",variant="warning"), Label(id="input_pubkey", classes="value-label")),
                        Horizontal(Label("PrivKey:", classes="field-label"), Label(id="input_privkey", classes="value-label")),
                        Horizontal(Label("Address:", classes="field-label"), Label(id="input_address", classes="value-label")),
                        Horizontal(Label("Puerto:", classes="field-label"), Label(id="input_port", classes="value-label")),
                        Horizontal(Label("DNS:", classes="field-label"), Label(id="input_dns", classes="value-label")),
                        Horizontal(Label("Endpoint:", classes="field-label"), Label(id="input_endpoint", classes="value-label")),
                        classes="details-container") , # Cambiado de details-grid
                    DataTable(id="clients_table", classes="clients-table"),
                    Horizontal(
                        Link("add client", id="add_client"),
                    ),
                )
            
            )

 


class Add_client(ModalScreen):
    """A widget to add a client."""
    def __init__(self, input_label: str) -> None:
        self.input_label = input_label
        super().__init__()

    def compose(self) -> ComposeResult:  
        yield Label(self.input_label)
        yield Input()

class Edit_client(ModalScreen):
    """A widget to edit a client."""
    def __init__(self, input_label: str) -> None:
        self.input_label = input_label
        super().__init__()

    def compose(self) -> ComposeResult:  
        yield Label(self.input_label)
        yield Input()

class Delete_client(ModalScreen):
    """A widget to delete a client."""
    def __init__(self, input_label: str) -> None:
        self.input_label = input_label
        super().__init__()

    def compose(self) -> ComposeResult:  
        yield Label(self.input_label)
        yield Input()


class Add_server(ModalScreen):
    """A widget to add a server."""
    def __init__(self, input_label: str) -> None:
        self.input_label = input_label
        super().__init__()

    def compose(self) -> ComposeResult:  
        yield Label(self.input_label)
        yield Input()
class Edit_server(ModalScreen):
    """A widget to edit a server."""
    def __init__(self, input_label: str) -> None:
        self.input_label = input_label
        super().__init__()

    def compose(self) -> ComposeResult:  
        yield Label(self.input_label)
        yield Input()

class Delete_server(ModalScreen):
    """A widget to delete a server."""
    def __init__(self, input_label: str) -> None:
        self.input_label = input_label
        super().__init__()

    def compose(self) -> ComposeResult:  
        yield Label(self.input_label)
        yield Input()

class Close(ModalScreen):
    """A widget to close the app."""
    def __init__(self, input_label: str) -> None:
        self.input_label = input_label
        super().__init__()

    def compose(self) -> ComposeResult:  
        yield Label(self.input_label)
        yield Input()

 # Run the app
if __name__ == "__main__":
    app = TerminalUI()
    app.run()
