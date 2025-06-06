from textual import containers, on 
# Importar la clase principal de la aplicación y el tipo ComposeResult
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
# Importar los contenedores para organizar el layout
from textual.containers import Container, Vertical, Horizontal, Grid

# Importar los widgets básicos para la UI
from textual.widgets import Button, Label, Input, Static, Select,Switch

import json
from textual.widget import Widget
from textual.binding import Binding
import clients, servers
import uuid
import os
from confirm_msg import ConfirmModal

# Variable global para la ruta del archivo de datos, aunque es mejor pasarla como argumento o como atributo de la app.
# FILE_PATH_WG_DATA = "wg_data.json" # Ejemplo de constante

# Clase para la pantalla principal de la UI, con su propio borde y título
class MainAppUI(Static):

    def compose(self) -> ComposeResult:
        
        with containers.Container(classes="main-container"): # Contenedor interno
            yield Horizontal(
                Vertical(
                    Vertical( # Contenedor para el selector de servidor 
                        Vertical(
                            Horizontal(
                            Select([], id="select_server"),
                            Switch(id="enable_server")
                            ),
                            Label("Detalles del Servidor:", classes="details-header",variant="secondary"),
                            Vertical(
                                Horizontal(Label("PubKey:", classes="field-label"), Label(id="input_pubkey", classes="value-label")),
                                Horizontal(Label("Address:", classes="field-label"), Label(id="input_address", classes="value-label")),
                                Horizontal(Label("Puerto:", classes="field-label"), Label(id="input_port", classes="value-label")),
                                Horizontal(Label("DNS:", classes="field-label"), Label(id="input_dns", classes="value-label")),
                                Horizontal(Label("Endpoint:", classes="field-label"), Label(id="input_endpoint", classes="value-label")),
                                classes="details-container"
                            ),
                            Horizontal(
                                Button("Configurar", id="btn_configure_server", variant="primary"), 
                                Button("Nuevo", id="btn_add_server", variant="default"),
                                Button("Eliminar", id="btn_delete_server", variant="error",) 
                            ),
                            id="select_server",
                            classes="select-server-container"
                        ),

                        Horizontal(
                         
                                Select([], id="select_client"),
                                Switch(id="enable_client"),
                                id="select_client_h",
                                classes="select-client-container" 
                            ),
                        Horizontal(   
                            Vertical(
                                Label("Detalles del Cliente:", classes="details-header",variant="primary"),
                                Horizontal(Label("Name:", classes="field-label"), Label(id="name_client", classes="value-label")),
                                Horizontal(Label("PubKey:", classes="field-label"), Label(id="input_pubkey_client", classes="value-label")),
                                Horizontal(Label("Address:", classes="field-label"), Label(id="input_address_client", classes="value-label")),
                                Horizontal(Label("DNS:", classes="field-label"), Label(id="input_dns_client", classes="value-label")),
                               
                                classes="details-container"
                            ),
                            classes="server-details-container" 
                         ),
                    #'default', 'error', 'primary', 'success', or 'warning'
                    Horizontal(
                        Button("Editar Cliente", id="btn_edit_client", classes="list-btn"), 
                        Button("Eliminar Cliente", id="btn_delete_client", classes="list-btn", variant="error"), 
                        Button("Nuevo",id="add_client"),
                        classes="button-row"
                    ),
                    classes="main-details-vertical" # Clase CSS opcional para la columna vertical principal
                    ),
                ),
                classes="horizontal-container", id="main_app_ui_container" # Clase CSS opcional para el contenedor horizontal principal
            )
            

# Clase principal de la aplicación
class TerminalUI(App):


    TITLE = "WG-TUI - WireGuard Manager" # Título de la ventana de la aplicación
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = "styles.css"

    async def refresh_server_select(self):
        selct_server = self.query_one("#select_server", Select)
        select_client = self.query_one("#select_client", Select)
        previous_value_server = selct_server.value
        self.previous_value_client = select_client.value


        # Recarga servidores
        selct_server.clear()
        list_cl = [(server_id["name"], id_) for id_, server_id in self.wg_data["servers"].items()]
        selct_server.set_options(list_cl)
        # Restaurar selección de servidor
        if previous_value_server in self.wg_data["servers"]:
            selct_server.value = previous_value_server
        else:
            selct_server.value = Select.BLANK

    async def on_mount(self) -> None:
        """Carga datos y refresca la lista al iniciar."""
        self.theme = "flexoki"
        self.load_data("wg_data.json") # Considera usar una constante o atributo de clase para "wg_data.json"
        self.query_one("#main_app_ui_container", Horizontal).border_title = "WG-TUI - A simple terminal interface for WireGuard" 
        self.query_one("#select_server", Vertical).border_title = "Selecciona un servidor"
        self.query_one("#select_client_h",Horizontal).border_title = "Selecciona un cliente"
        await self.refresh_server_select()

    def load_data(self, path_json: str):
        """Carga wg_data desde un archivo JSON."""
        try:
            with open(path_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.wg_data = data  # Siempre el objeto raíz
            if "servers" not in data:
                self.notify("La clave 'servers' no se encontró en el JSON. Usando datos raíz.", severity="warning", title="Advertencia de Carga")
        except FileNotFoundError:
            self.notify(f"Cree un nuevo servidor para empezar.", severity="information", title="No se encontro archivo de configuracion.")
            self.wg_data = {"servers": {}}
            new_id_server = str(uuid.uuid4())
            modal = servers.Add_edit_server(new_id_server, self, True, previous_screen=self)
            self.push_screen(modal)
        except json.JSONDecodeError:
            self.notify(f"Error decodificando JSON en el archivo: {path_json}", severity="error", title="Error de Carga")
            self.wg_data = {"servers": {}}
        except Exception as e:
            self.notify(f"Error inesperado al cargar datos: {e}", severity="error", title="Error de Carga")
            self.wg_data = {"servers": {}}
    
    def on_switch_changed(self, event:Switch.Changed) -> None:
        try:
            if event.switch.id == "enable_server":
                self.wg_data["servers"][self.query_one("#select_server",Select).value]["enable"]= event.switch.value
            elif event.switch.id == "enable_client":
                self.wg_data["servers"][self.query_one("#select_server",Select).value]["clients"][self.query_one("#select_client",Select).value]["enable"]= event.switch.value
                
            with open("wg_data.json", 'w', encoding='utf-8') as f:
                    json.dump(self.wg_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.notify(f"Error al guardar el estado: {e}", severity="error", title="Error de Guardado")
            return



    def on_select_changed(self, event: Select.Changed) -> None:
        try:
            """Manejador de eventos para cambios en los selectores."""
            if event.select.id == "select_server":
                selected_server_id = event.value
                select_client = self.query_one("#select_client", Select)
                if selected_server_id is Select.BLANK or not self.wg_data.get("servers"):
                    select_client.clear()
                    self.query_one("#select_client", Select).clear()
                    self.query_one("#input_pubkey", Label).update("")
                    self.query_one("#input_address", Label).update("")
                    self.query_one("#input_port", Label).update("")
                    self.query_one("#input_dns", Label).update("")
                    self.query_one("#input_endpoint", Label).update("")
                    return

                server_id = self.wg_data.get("servers", {}).get(selected_server_id)
                if not server_id:
                    self.notify(f"No se encontró el servidor seleccionado: {selected_server_id}", severity="error", title="Error de Datos")
                    return

                self.query_one("#input_pubkey", Label).update(server_id.get("publicKey", ""))
                self.query_one("#input_address", Label).update(server_id.get("address", ""))
                self.query_one("#input_port", Label).update(str(server_id.get("port", "")))
                self.query_one("#input_dns", Label).update(server_id.get("dns", ""))
                self.query_one("#input_endpoint", Label).update(server_id.get("endpoint", ""))
                self.query_one("#enable_server", Switch).value = server_id.get("enable", False)
                
                select_client.clear()
                clients_dict = server_id.get("clients", {})
                clients = []
                for client_id, client_data in clients_dict.items():
                    name_id = client_data.get("name", "")
                    clients.append((name_id, client_id))
                select_client.set_options(clients)
                # Restaurar selección de cliente si existe
                if self.previous_value_client in clients_dict:
                    select_client.value = self.previous_value_client
                else:
                    select_client.value = Select.BLANK
            elif event.select.id == "select_client":
                server_id = self.query_one("#select_server", Select).value
                selected_client_id = event.value

                if selected_client_id is Select.BLANK or not self.wg_data.get("servers", {}).get(self.query_one("#select_server", Select).value, {}).get("clients", {}):
                    self.query_one("#name_client", Label).update("")
                    self.query_one("#input_pubkey_client", Label).update("")
                    self.query_one("#input_address_client", Label).update("")
                    self.query_one("#input_dns_client", Label).update("")
                    return

                client_data = self.wg_data.get("servers", {}).get(server_id, {}).get("clients", {}).get(selected_client_id, {})
                if not client_data:
                    self.notify(f"No se encontró el servidor cliente.", severity="error", title="Error de Datos")
                    return

                self.query_one("#name_client", Label).update(client_data.get("name", ""))
                self.query_one("#input_pubkey_client", Label).update(client_data.get("publicKey", ""))
                self.query_one("#input_address_client", Label).update(client_data.get("address", ""))
                self.query_one("#input_dns_client", Label).update(client_data.get("dns", ""))
                self.query_one("#enable_client", Switch).value = client_data.get("enable", False)
        except Exception as e:
            self.notify(f"Error con la selección: {e}", severity="error", title="Error de Selección")
            return


  
    @on(Button.Pressed, "#add_client")
    def add_client_handler(self, event: Button.Pressed) -> None:
        new_id_client = str(uuid.uuid4())
        selected_server = self.query_one("#select_server", Select)
        if selected_server.value == Select.BLANK:
            self.notify("Tienes que es escoger un servidor para agerar un cliente.", severity="warning", title="Selecciona un servidor.")
            return
        modal = clients.Add_edit_client(selected_server.value, new_id_client, self, False , previous_screen=self)
        self.push_screen(modal)

    @on(Button.Pressed, "#btn_edit_client")
    def edit_client_handler(self, event: Button.Pressed) -> None:
        """Abre el modal para editar un cliente."""
        selected_server = self.query_one("#select_server", Select)
        selected_client = self.query_one("#select_client", Select)
        if selected_server.value == Select.BLANK:
            self.notify("Por favor selecciona un servidor primero.", severity="error", title="Error de Selección")
            return
        
        if selected_client.value == Select.BLANK:
            self.notify("Por favor selecciona un cliente primero.", severity="error", title="Error de Selección")
            return
        modal = clients.Add_edit_client(selected_server.value, selected_client.value, self, True , previous_screen=self)
        self.push_screen(modal)

    @on(Button.Pressed, "#btn_add_server")
    def btn_add_server_handler(self)-> None:
        new_id_server = str(uuid.uuid4())
        modal = servers.Add_edit_server(new_id_server, True, previous_screen=self)
        self.push_screen(modal)
        
    @on(Button.Pressed, "#btn_delete_server")
    def btn_delete_server_handler(self, event: Button.Pressed) -> None:
        selected_server = self.query_one("#select_server", Select)
        if selected_server.value == Select.BLANK:
            self.notify("Por favor selecciona un servidor primero.", severity="error", title="Error de Selección")
            return
        name = self.wg_data.get("servers",{}).get(selected_server.value,{}).get("name",{})

        modal = ConfirmModal(
            f"¿Estás seguro de que deseas eliminar el Servidor '{name}'?\nEsta acción no se puede deshacer.",
            on_confirm=lambda: self.del_reg(selected_server.value, None, name)
        )
        self.push_screen(modal)
    
    @on(Button.Pressed, "#btn_delete_client")
    def delete_client_handler(self, event: Button.Pressed) -> None:
        selected_server = self.query_one("#select_server", Select)
        selected_client = self.query_one("#select_client", Select)
        if selected_server.value == Select.BLANK:
            self.notify("Por favor selecciona un servidor primero.", severity="error", title="Error de Selección")
            return
        if selected_client.value == Select.BLANK:
            self.notify("Por favor selecciona un cliente primero.", severity="error", title="Error de Selección")
            return
        name = self.query_one("#name_client", Label).renderable

        modal = ConfirmModal(
            f"¿Estás seguro de que deseas eliminar el cliente '{name}'? Esta acción no se puede deshacer.",
            on_confirm=lambda: self.del_reg(selected_server.value, selected_client.value, name)
        )
        self.push_screen(modal)

        
    async def del_reg(self,id_server,id_client,item_name):
        try:
            if id_client == None:
                del self.wg_data["servers"][id_server]
            else:
                del self.wg_data["servers"][id_server]["clients"][id_client]
            with open("wg_data.json", "w", encoding="utf-8") as f:
                json.dump(self.wg_data, f, indent=2, ensure_ascii=False)
            self.notify(f"'{item_name}' fue eliminado correctamente.", severity="success", title="Eliminado")
            await self.refresh_server_select()
        except Exception as e:
            self.notify(f"Error al eliminar {item_name}: {e}", severity="error", title="Error")
            
    def compose(self) -> ComposeResult:
        """Compone la UI principal de la aplicación."""
        yield MainAppUI(
            id="main_app_ui_container",
            classes="main_app_ui_frame" # Clase para estilizar el borde en CSS
        )

# --- Bloque de ejecución ---
if __name__ == "__main__":
    app = TerminalUI()
    app.run()
