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

# Variable global para la ruta del archivo de datos, aunque es mejor pasarla como argumento o como atributo de la app.
# FILE_PATH_WG_DATA = "wg_data.json" # Ejemplo de constante

# Clase para la pantalla principal de la UI, con su propio borde y título
class MainAppUI(Static):
    def __init__(self, title_text: str, info_widget: Static, **kwargs) -> None:
        # Extraer 'border_title' de kwargs antes de pasarlos a super().__init__()
        # ya que Static no lo espera como argumento de inicialización.
        border_title_value = kwargs.pop("border_title", None)
        
        super().__init__(**kwargs) # Ahora kwargs no contiene 'border_title'
        
        # Asignar el border_title como un atributo de la instancia si se proporcionó.
        if border_title_value:
            self.border_title = border_title_value
            
        self.title_text_widget = Static(title_text, classes="header-box") # El Static que antes mostraba BORDER_TITLE
        self.info_widget = info_widget # El Static "by malak96"
    def compose(self) -> ComposeResult:
        with containers.Container(classes="main-container"): # Contenedor interno
            yield self.title_text_widget
            yield self.info_widget
            
            yield Horizontal(    
                Vertical(
                    Vertical( # Contenedor para el selector de servidor
                        Label("Selecciona un servidor:"), # Corregido typo
                        Select([], id="select_instance"),
                        classes="server-selection-box" # Clase CSS opcional para estilizar
                    ),
                    Static(), # Espaciador o contenido adicional
                    Label("Detalles del Servidor:", classes="details-header"), # Título para la sección de detalles
                    Vertical(
                        Horizontal(Label("PubKey:", classes="field-label",variant="warning"), Label(id="input_pubkey", classes="value-label")),
                        Horizontal(Label("PrivKey:", classes="field-label"), Label(id="input_privkey", classes="value-label")),
                        Horizontal(Label("Address:", classes="field-label"), Label(id="input_address", classes="value-label")),
                        Horizontal(Label("Puerto:", classes="field-label"), Label(id="input_port", classes="value-label")),
                        Horizontal(Label("DNS:", classes="field-label"), Label(id="input_dns", classes="value-label")),
                        Horizontal(Label("Endpoint:", classes="field-label"), Label(id="input_endpoint", classes="value-label")),
                        classes="details-container"
                    ),
                    DataTable(id="clients_table", classes="clients-table"),
                    Horizontal(
                        Link("Añadir Cliente", id="add_client", classes="action-link"), # Texto más descriptivo
                        classes="client-actions-bar" # Clase CSS opcional
                    ),
                    Horizontal(
                        Button("Editar Cliente", id="btn_edit_client", classes="list-btn"), # Texto más descriptivo
                        Button("Eliminar Cliente", id="btn_delete_client", classes="list-btn", variant="error"), # Texto más descriptivo
                        classes="button-row"
                    ),
                    classes="main-content-column" # Clase CSS opcional para la columna vertical principal
                ),
                classes="top-level-horizontal-layout" # Clase CSS opcional
            )

# Clase principal de la aplicación
class TerminalUI(App):
    TITLE = "WG-TUI - WireGuard Manager" # Título de la ventana de la aplicación
    ENABLE_COMMAND_PALETTE = False
    
    CSS_PATH = "styles.css"

    # Widget estático para información adicional
    info_widget = Static("by malak96", classes="info-footer-box")

    # Texto para el título principal dentro de la UI
    main_ui_title_text = "WG-TUI - A simple terminal interface for WireGuard"

    async def refresh_instances_list(self):
        """Actualiza el ListView de instancias según wg_data."""
        selct_instance = self.query_one("#select_instance", Select)
        selct_instance.clear() # Usar clear_options() para Select
        list_cl = []
        # Asumiendo que "servers" es la clave correcta en tu JSON y self.wg_data está inicializado
        for name, instance in self.wg_data.get("servers", {}).items():
            # (Texto a mostrar en el Select, valor interno del item)
            list_cl.append((instance.get("name", name), name))

        if list_cl:
            selct_instance.set_options(list_cl)
        else:
            selct_instance.prompt = "No hay servidores disponibles" # Mensaje si no hay opciones

    async def on_mount(self) -> None:
        """Carga datos y refresca la lista al iniciar."""
        self.theme = "nord" # Establecer el tema de la aplicación
        self.load_wg_data_from_json("wg_data.json") # Considera usar una constante o atributo de clase para "wg_data.json"
        await self.refresh_instances_list()
        clients_table = self.query_one("#clients_table", DataTable)
        clients_table.cursor_type = "row"
        clients_table.zebra_stripes = True

    def load_wg_data_from_json(self, file_path_arg: str):
        """Carga wg_data desde un archivo JSON."""
        try:
            with open(file_path_arg, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Asegúrate que la clave "servers" (o "servrs" si es un typo intencional en tu JSON) es la correcta.
            self.wg_data = data.get("servers", data) # Usando "servers" como la clave esperada
            if "servers" not in data:
                 self.notify("La clave 'servers' no se encontró en el JSON. Usando datos raíz.", severity="warning", title="Advertencia de Carga")
        except FileNotFoundError:
            self.notify(f"Archivo no encontrado: {file_path_arg}", severity="error", title="Error de Carga")
            self.wg_data = {"servers": {}} # Inicializar para evitar errores en refresh_instances_list
        except json.JSONDecodeError:
            self.notify(f"Error decodificando JSON en el archivo: {file_path_arg}", severity="error", title="Error de Carga")
            self.wg_data = {"servers": {}}
        except Exception as e:
            self.notify(f"Error inesperado al cargar datos: {e}", severity="error", title="Error de Carga")
            self.wg_data = {"servers": {}}

    @on(Select.Changed, "#select_instance")
    def select_client_handler(self, event: Select.Changed) -> None:
        """Actualiza el DataTable de clientes al seleccionar un cliente."""
        selected_instance_id = event.value
        
        # Si no hay selección o no hay datos de servidores, limpiar los campos.
        if selected_instance_id is Select.BLANK or not self.wg_data.get("servers"):
            self.query_one("#input_pubkey", Label).update("N/D")
            self.query_one("#input_privkey", Label).update("N/D")
            self.query_one("#input_address", Label).update("N/D")
            self.query_one("#input_port", Label).update("N/D")
            self.query_one("#input_dns", Label).update("N/D")
            self.query_one("#input_endpoint", Label).update("N/D")
            self.query_one("#clients_table", DataTable).clear()
            return

        instance = self.wg_data.get("servers", {}).get(selected_instance_id)
        if not instance:
            self.notify(f"No se encontró la instancia seleccionada: {selected_instance_id}", severity="error", title="Error de Datos")
            return

        self.query_one("#input_pubkey", Label).update(instance.get("publicKey", "N/D"))
        self.query_one("#input_privkey", Label).update(instance.get("privateKey", "N/D"))
        self.query_one("#input_address", Label).update(instance.get("address", "N/D"))
        self.query_one("#input_port", Label).update(str(instance.get("port", "N/D")))
        self.query_one("#input_dns", Label).update(instance.get("dns", "N/D"))
        self.query_one("#input_endpoint", Label).update(instance.get("endpoint", "N/D"))

        clients_table = self.query_one("#clients_table", DataTable)
        clients_table.clear()
        if not clients_table.columns:
            clients_table.add_columns("Nombre", "Dirección", "Clave Pública", "AllowedIPs", "Habilitado")
        
        clients_dict = instance.get("clients", {})
        for client_id, client_data in clients_dict.items():
            clients_table.add_row(
                client_data.get("name", "N/D"),
                client_data.get("address", "N/D"),
                client_data.get("publicKey", "N/D"),
                client_data.get("allowedIPs", "N/D"),
                "Sí" if client_data.get("enabled", False) else "No",
                key=client_id # Añadir clave para posible referencia futura si es necesario
            )

    def compose(self) -> ComposeResult:
        """Compone la UI principal de la aplicación."""
        yield MainAppUI(
            title_text=self.main_ui_title_text,
            info_widget=self.info_widget,
            border_title="Panel de Control WireGuard", # Título para el borde del contenedor principal
            id="main_app_ui_container",
            classes="main_app_ui_frame" # Clase para estilizar el borde en CSS
        )

# --- Clases Modales ---
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

# --- Bloque de ejecución ---
if __name__ == "__main__":
    app = TerminalUI()
    app.run()
