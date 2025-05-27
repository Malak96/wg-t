from textual import containers, on 
# Importar la clase principal de la aplicación y el tipo ComposeResult
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
# Importar los contenedores para organizar el layout
from textual.containers import Container, Vertical, Horizontal, Grid

# Importar los widgets básicos para la UI
from textual.widgets import Button, ListView, ListItem, Label, Input, Static, DataTable, Select

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
                        Horizontal(
                            Select([], id="select_instance"),
                            Button("Añadir Servidor", id="btn_add_server", variant="primary"), # Botón para añadir un servidor
                        ),
                        Label("Selecciona un cliente"),
                        Select([], id="select_client",type_to_search = True),
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
                    #'default', 'error', 'primary', 'success', or 'warning'
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
        selct_instance.clear()
        list_cl = []
        # Asegúrate de iterar sobre los servidores, no sobre el diccionario raíz
        for name, instance in self.wg_data["servers"].items():
            # Añadir opciones al Select
            list_cl.append((name, instance["name"]))
        # Añadir opciones al Select 
        selct_instance.set_options(list_cl)

    async def on_mount(self) -> None:
        """Carga datos y refresca la lista al iniciar."""
        self.theme = "flexoki" 
        self.load_data("cli/wg_data.json") # Considera usar una constante o atributo de clase para "wg_data.json"
        await self.refresh_instances_list()

    def load_data(self, path_json: str):
        """Carga wg_data desde un archivo JSON."""
        try:
            with open(path_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.wg_data = data  # Siempre el objeto raíz
            if "servers" not in data:
                self.notify("La clave 'servers' no se encontró en el JSON. Usando datos raíz.", severity="warning", title="Advertencia de Carga")
        except FileNotFoundError:
            self.notify(f"Archivo no encontrado: {path_json}", severity="error", title="Error de Carga")
            self.wg_data = {"servers": {}}
        except json.JSONDecodeError:
            self.notify(f"Error decodificando JSON en el archivo: {path_json}", severity="error", title="Error de Carga")
            self.wg_data = {"servers": {}}
        except Exception as e:
            self.notify(f"Error inesperado al cargar datos: {e}", severity="error", title="Error de Carga")
            self.wg_data = {"servers": {}}

    @on(Select.Changed, "#select_instance")
    def select_server_handler(self, event: Select.Changed) -> None:
        """Actualiza el DataTable de clientes al seleccionar un cliente."""
        selected_instance_id = event.value
        slect_client = self.query_one("#select_client", Select)
        # Si no hay selección o no hay datos de servidores, limpiar los campos.
        if selected_instance_id is Select.BLANK or not self.wg_data.get("servers"):
            slect_client.set_options([])
            self.query_one("#select_client", Select).clear()
            self.query_one("#input_pubkey", Label).update("N/D")
            self.query_one("#input_privkey", Label).update("N/D")
            self.query_one("#input_address", Label).update("N/D")
            self.query_one("#input_port", Label).update("N/D")
            self.query_one("#input_dns", Label).update("N/D")
            self.query_one("#input_endpoint", Label).update("N/D")
            return

        instance = self.wg_data.get("servers", {}).get(selected_instance_id)
        if not instance:
            self.notify(f"No se encontró el servidor seleccionado: {selected_instance_id}", severity="error", title="Error de Datos")
            return

        self.query_one("#input_pubkey", Label).update(instance.get("publicKey", "N/D"))
        self.query_one("#input_privkey", Label).update(instance.get("privateKey", "N/D"))
        self.query_one("#input_address", Label).update(instance.get("address", "N/D"))
        self.query_one("#input_port", Label).update(str(instance.get("port", "N/D")))
        self.query_one("#input_dns", Label).update(instance.get("dns", "N/D"))
        self.query_one("#input_endpoint", Label).update(instance.get("endpoint", "N/D"))

        slect_client.clear()
        clients_dict = instance.get("clients", {})
        clients = []
        for client_id, client_data in clients_dict.items():
            name_id = client_data.get("name", "N/D") + " (" + client_id + ")"
            clients.append((name_id, client_id))

        slect_client.set_options(clients)

    @on(Button.Pressed, "#btn_edit_client")
    def edit_client_handler(self, event: Button.Pressed) -> None:
        """Abre el modal para editar un cliente."""
        selected_server = self.query_one("#select_instance", Select)
        selected_client = self.query_one("#select_client", Select)
        if selected_server.value == Select.BLANK:
            self.notify("Por favor selecciona un servidor primero.", severity="error", title="Error de Selección")
            return
        
        if selected_client.value == Select.BLANK:
            self.notify("Por favor selecciona un cliente primero.", severity="error", title="Error de Selección")
            return
        modal = Edit_client(selected_server.value, selected_client.value, self, previous_screen=self)
        self.push_screen(modal)

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
    def __init__(self, id_server: str, previous_screen: None) -> None:
        self.previous_screen = previous_screen
        self.id_server = id_server
        super().__init__()

class Edit_client(ModalScreen):
    """A widget to edit a client."""
    def __init__(self, id_server: str, id_client: str, app_ref, previous_screen: None) -> None:
        self.previous_screen = previous_screen
        self.id_server = id_server
        self.id_client = id_client
        self.app_ref = app_ref
        super().__init__()

    def compose(self) -> ComposeResult:  
        yield Vertical(
                        Horizontal(
                Label("privKey:", classes="label_edit_client"),
                Input(id="input_private_key", classes="input_edit_client", password=True),
                Button("Mostrar", id="btn_show_private_key", variant="success",classes="edit_client_keys")
            ),
            Horizontal(
                Label("pubKey:", classes="label_edit_client"),
                Input(id="input_public_key", classes="input_edit_client"),
                Button("Cambiar", id="btn_show_public_key", variant="default", classes="edit_client_keys")
            ),
            Horizontal(
                Label("presharedKey:", classes="label_edit_client"),
                Input(id="input_preshared_key", classes="input_edit_client"),
                Button("⟳", id="btn_show_preshared_key", variant="primary", classes="edit_client_keys")
            ),
            Horizontal(
                Label("name:", classes="label_edit_client"),
                Input(id="name_client", classes="input_edit_client"),
                Label("address:", classes="label_edit_client"),
                Input(id="input_client_address", classes="input_edit_client")),
          
            Horizontal(
                Label("DNS:", classes="label_edit_client"),
                Input(id="input_dns", classes="input_edit_client"),
                Label("Keepalive:", classes="label_edit_client"),
                Input(id="input_persistent_keepalive", classes="input_edit_client")
            ),
            Horizontal(
                Label("allowedIPs:", classes="label_edit_client"),
                Input(id="input_allowed_ips", classes="input_edit_client"),
                Label("Habilitado:", classes="label_edit_client"),
                Select([("Sí", True), ("No", False)], allow_blank=False, id="select_enabled")
            ),
            Horizontal(
                Button("Guardar",id="btn_save_client",variant="primary",classes="list-btn"),
                Button("Cancelar",id="btn_cancel_client", variant="error", classes="list-btn")
            )
            ,id="Edit_client"
        )

    async def _on_mount(self) -> None:
        """Método para manejar el evento de montaje."""
        await self.load_client_data()  # Cargar datos del cliente al montar

    async def load_client_data(self):
        """Carga los datos del cliente."""
        valor = self.app_ref.wg_data.get("servers", {}).get(self.id_server, {}).get("clients", {}).get(self.id_client, {})
        self.query_one("#name_client", Input).value = valor.get("name", "") or ""
        self.query_one("#input_client_address", Input).value = valor.get("address", "") or ""
        self.query_one("#input_private_key", Input).value = valor.get("privateKey", "") or ""
        self.query_one("#input_public_key", Input).value = valor.get("publicKey", "") or ""
        self.query_one("#input_preshared_key", Input).value = valor.get("PresharedKey", "") or ""
        self.query_one("#input_dns", Input).value = valor.get("dns", "") or ""
        self.query_one("#input_persistent_keepalive", Input).value = str(valor.get("persistentKeepalive", "")) or ""
        self.query_one("#input_allowed_ips", Input).value = valor.get("allowedIPs", "") or ""
        self.query_one("#select_enabled", Select).value = valor.get("enabled", False)
    
    @on(Button.Pressed, "#btn_cancel_client")
    def cancelar(self, event: Button.Pressed) -> None:
        """Volver a la pantalla de inicio"""
        self.app.pop_screen()
    @on(Button.Pressed, "#btn_show_private_key")
    def btn_show_private_key(self, event: Button.Pressed) -> None:
        """Mostrar la clave privada."""
        priv_key_input = self.query_one("#input_private_key", Input)
        Button_name = self.query_one("#btn_show_private_key", Button)
        if priv_key_input.password == True:
            priv_key_input.password = False
            Button_name.label = "Ocultar"
        else:
            priv_key_input.password = True
            Button_name.label = "Mostrar"
        #priv_key_input.focus()


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
