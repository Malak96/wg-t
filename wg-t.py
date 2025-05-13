import json
import os
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    Select,
    TabbedContent,
    TabPane,
)

# Nombre del archivo de configuración de WireGuard
WG_CONFIG_FILE = "wg0.json"

class MainScreen(Screen):
    """Pantalla principal de la aplicación con pestañas."""

    BINDINGS = [
        ("q", "quit_app", "Salir"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La configuración de temas se ha eliminado por ahora

    def load_clients_data(self) -> list[dict]:
        """
        Carga y procesa los datos de los clientes desde el archivo WG_CONFIG_FILE.
        Devuelve una lista de diccionarios, donde cada diccionario representa un cliente.
        """
        if not os.path.exists(WG_CONFIG_FILE):
            self.notify(
                f"Advertencia: El archivo '{WG_CONFIG_FILE}' no existe.",
                severity="warning",
                timeout=5,
            )
            return []

        try:
            with open(WG_CONFIG_FILE, "r", encoding="utf-8") as f:
                data_from_file = json.load(f)
        except json.JSONDecodeError:
            self.notify(
                f"Error: El archivo '{WG_CONFIG_FILE}' no contiene un JSON válido.",
                severity="error",
                timeout=5,
            )
            return []
        except Exception as e:
            self.notify(
                f"Error inesperado al leer '{WG_CONFIG_FILE}': {e}",
                severity="error",
                timeout=5,
            )
            return []

        clients_dict = data_from_file.get("clients")

        if clients_dict is None:
            self.notify(
                f"Error: La clave 'clients' no se encuentra en '{WG_CONFIG_FILE}'.",
                severity="error",
                timeout=5,
            )
            return []

        if not isinstance(clients_dict, dict):
            self.notify(
                f"Error: La sección 'clients' en '{WG_CONFIG_FILE}' no es un diccionario.",
                severity="error",
                timeout=5,
            )
            return []

        processed_clients = []
        for client_json_key, client_info in clients_dict.items():
            if isinstance(client_info, dict):
                # Creamos un nuevo diccionario para cada cliente,
                # añadiendo la clave UUID del JSON como un campo más.
                current_client_data = {"json_key_uuid": client_json_key}
                current_client_data.update(client_info)
                processed_clients.append(current_client_data)
            else:
                self.notify(
                    f"Advertencia: Datos para cliente con clave '{client_json_key}' tienen formato incorrecto y serán omitidos.",
                    severity="warning",
                    timeout=3,
                )
        return processed_clients

    async def populate_clients_tab(self) -> None:
        """Carga los datos de los clientes y los muestra en la pestaña 'Clientes'."""
        clients_data = self.load_clients_data()
        clients_list_container = self.query_one("#clients_list_container", VerticalScroll)

        # Limpiar contenido previo (ej. mensaje de "Cargando...")
        await clients_list_container.remove_children()

        if not clients_data:
            await clients_list_container.mount(
                Label("No se encontraron clientes o hubo un error al cargar.")
            )
            return

        for i, client in enumerate(clients_data):
            await clients_list_container.mount(
                Label(f"--- Cliente #{i + 1} ---", classes="client_header")
            )
            for key, value in client.items():
                field_name_formatted = str(key).replace("_", " ").capitalize()
                # Convertir listas o diccionarios a string para visualización simple
                if isinstance(value, (list, dict)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)
                await clients_list_container.mount(
                    Label(f"  {field_name_formatted}: {value_str}")
                )
            if i < len(clients_data) - 1:
                 await clients_list_container.mount(Label(" ")) # Espacio entre clientes

        self.notify("Clientes cargados.", timeout=2)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="main_tabs"):
            with TabPane("Inicio", id="tab_inicio"):
                with Vertical(classes="pane_content"):
                    yield Label("Bienvenido al Gestor de Clientes WG-T", classes="welcome_message")
                    yield Label("Utiliza las pestañas para navegar por la aplicación.")
                    yield Button("Recargar Clientes (Pestaña Clientes)", id="reload_clients_btn", classes="action_button")

            with TabPane("Clientes", id="tab_clientes"):
                with VerticalScroll(id="clients_list_container", classes="pane_content"):
                    yield Label("Cargando clientes...", id="clients_loading_label")

        yield Footer()

    async def on_mount(self) -> None:
        """Se llama cuando la pantalla está montada."""
        # Cargar clientes al iniciar la pestaña de clientes
        # Opcionalmente, puedes hacer que se carguen solo cuando se active la pestaña
        await self.populate_clients_tab()
        # La lógica de configuración de temas se ha eliminado


    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Maneja los eventos de clic en los botones."""
        button_id = event.button.id
        
        if button_id == "reload_clients_btn":
            self.notify("Recargando lista de clientes...", timeout=1)
            # Asegurarse de que la pestaña de clientes esté activa o simplemente recargar
            # los datos y la próxima vez que se vea la pestaña, estarán actualizados.
            # Para forzar la actualización visual si la pestaña no está activa,
            # sería más complejo. Por ahora, solo recargamos los datos.
            clients_list_container = self.query_one("#clients_list_container", VerticalScroll)
            clients_list_container.query("*").remove() # Limpiar antes de repoblar
            clients_list_container.mount(Label("Recargando clientes...", id="clients_loading_label"))
            self.run_worker(self.populate_clients_tab, exclusive=True)


    def action_quit_app(self) -> None:
        """Sale de la aplicación."""
        self.app.exit("Aplicación cerrada por el usuario.")


class ClientManagerApp(App[None]):
    """Aplicación Textual para gestionar clientes de WireGuard."""

    TITLE = "Gestor de Clientes WG-T"
    # CSS_PATH = "styles.css" # Descomenta si tienes un archivo CSS

    # Estilos CSS básicos integrados para mejorar la apariencia
    DEFAULT_CSS = "" # Todos los estilos personalizados eliminados

    def on_mount(self) -> None:
        """Monta la pantalla principal de la aplicación."""
        self.push_screen(MainScreen())


if __name__ == "__main__":
    app = ClientManagerApp()
    app.run()
