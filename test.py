import json
from pathlib import Path # Para manejar rutas de archivos
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Static, Label
from textual.message import Message

MAX_ITEMS_PER_ROW = 3
# Ya no necesitamos ITEM_TEXT_CONTENT, usaremos datos del JSON

# Nombre del archivo JSON de donde se cargarán los datos
CLIENT_DATA_FILE = "wg0.json" 

class ItemContainer(Static):
    """
    Un contenedor para mostrar información de un cliente con un borde,
    título (nombre del cliente) y botón de eliminar.
    """

    class RemoveItem(Message):
        """Mensaje para indicar que este item debe ser eliminado."""
        def __init__(self, item_to_remove: "ItemContainer"):
            self.item_to_remove = item_to_remove
            super().__init__()

    def __init__(self, item_id: int, client_data: dict, **kwargs) -> None:
        super().__init__(**kwargs) 
        self.item_id = item_id # ID para la gestión interna de la UI
        self.client_data = client_data # Datos del cliente del JSON
        self.add_class("item_container")
        # Usar el nombre del cliente para el título del borde, o un fallback
        self.border_title = self.client_data.get("name", f"Elemento {self.item_id}")

    def compose(self) -> ComposeResult:
        """Compone el contenido del ItemContainer: datos del cliente y botón de eliminar."""
        with Vertical(classes="item_content_vertical"):
            client_name = self.client_data.get("name", "N/D") # N/D = No Disponible
            client_address = self.client_data.get("address", "N/D")
            client_enabled = self.client_data.get("enabled", "N/D")
            # Mostrar solo una parte de la clave pública para brevedad
            public_key_short = self.client_data.get("publicKey", "N/D")
            if public_key_short != "N/D" and len(public_key_short) > 20:
                public_key_short = public_key_short[:20] + "..."
            
            client_id_from_data = self.client_data.get("id", "N/D")

            display_text = (
                f"[b]Nombre:[/b] {client_name}\n"
                f"[b]Dirección IP:[/b] {client_address}\n"
                f"[b]Habilitado:[/b] {'Sí' if client_enabled else 'No'}\n"
                f"[b]PublicKey (inicio):[/b] {public_key_short}\n"
                f"[b]ID Cliente:[/b] {client_id_from_data}"
            )
            yield Label(display_text, classes="item_text_label", markup=True) # markup=True para [b]
            yield Button("Eliminar Este", variant="error", classes="remove_this_item_button")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.has_class("remove_this_item_button"):
            self.post_message(self.RemoveItem(self))
            event.stop()

class DynamicContainerApp(App):
    """
    Aplicación para mostrar datos de clientes de wg0.json en contenedores dinámicos.
    """

    CSS = """
    Screen {
        align: center middle; 
        background: $panel;
    }

    #main_layout {
        width: auto;
        height: auto;
        max-width: 90%;    
        max-height: 80%;   
        padding: 1;
        border: round $primary;
        background: $boost; 
    }

    #button_bar {
        height: auto;
        dock: top;          
        padding: 1;
        background: $primary-background;
    }

    #button_bar Button {
        width: 1fr;         
        margin: 0 1;
    }

    #content_area {
        width: 100%;
        height: 1fr;        
        padding: 1;
        border: round $primary-lighten-2;
        background: $surface;
        overflow-y: auto;   
        overflow-x: hidden; 
    }

    .row_container {
        height: auto;       
        margin-bottom: 1;   
        align: left top;    
    }

    .item_container {
        width: 1fr;         
        min-width: 35; /* Ajustado para más texto */
        height: auto;       
        padding: 1;
        margin: 0 1;        
        border: round $secondary;
        background: $primary-background-darken-1;
    }

    .item_content_vertical {
        height: auto; 
    }
    
    .item_text_label {
        margin-bottom: 1; 
        height: auto; 
    }

    .remove_this_item_button {
        width: 100%; 
    }
    """

    def __init__(self):
        super().__init__()
        self.ui_item_counter = 0 # Contador para los IDs de los widgets en la UI
        self.all_items_map: dict[int, ItemContainer] = {} # Mapa de widgets por su ui_item_counter
        
        self.clients_list: list[dict] = [] # Lista de datos de clientes del JSON
        self.client_idx_to_add = 0 # Índice del próximo cliente a agregar de la lista

    def _load_client_data(self) -> None:
        """Carga los datos de los clientes desde el archivo JSON."""
        json_file_path = Path(CLIENT_DATA_FILE)
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Extraer los clientes. En wg0.json, están bajo la clave "clients" como un diccionario.
            # Convertimos los valores de este diccionario en una lista.
            if "clients" in data and isinstance(data["clients"], dict):
                self.clients_list = list(data["clients"].values())
                self.notify(f"{len(self.clients_list)} clientes cargados desde {CLIENT_DATA_FILE}.", title="Datos Cargados")
            else:
                self.notify(f"La clave 'clients' no se encontró o no es un diccionario en {CLIENT_DATA_FILE}.", severity="warning", title="Error de Formato")
                self.clients_list = []

        except FileNotFoundError:
            self.notify(f"Archivo de datos '{CLIENT_DATA_FILE}' no encontrado.", severity="error", title="Error de Carga")
            self.clients_list = []
        except json.JSONDecodeError:
            self.notify(f"Error al decodificar JSON en '{CLIENT_DATA_FILE}'. Verifique el formato.", severity="error", title="Error de Carga")
            self.clients_list = []
        except Exception as e:
            self.notify(f"Error inesperado al cargar datos: {e}", severity="error", title="Error de Carga")
            self.clients_list = []


    async def on_mount(self) -> None:
        """Se llama cuando la aplicación se monta. Cargamos los datos aquí."""
        self._load_client_data()

    def compose(self) -> ComposeResult:
        with Vertical(id="main_layout"):
            with Horizontal(id="button_bar"):
                yield Button("Agregar Cliente", id="add_item", variant="success")
            yield VerticalScroll(id="content_area")

    def get_current_row_for_add(self) -> Horizontal | None:
        content_area = self.query_one("#content_area", VerticalScroll)
        rows = content_area.query(".row_container").filter("Horizontal")
        if rows:
            return rows[-1] 
        return None

    def add_new_row_for_add(self) -> Horizontal:
        content_area = self.query_one("#content_area", VerticalScroll)
        new_row = Horizontal()
        new_row.add_class("row_container")
        content_area.mount(new_row)
        return new_row

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add_item":
            if not self.clients_list:
                self.notify("No hay datos de clientes cargados para agregar.", severity="warning", title="Sin Datos")
                return
            
            if self.client_idx_to_add < len(self.clients_list):
                client_info = self.clients_list[self.client_idx_to_add]
                self.client_idx_to_add += 1
                
                self.ui_item_counter += 1 # Incrementa el contador para el ID del widget de UI
                new_item = ItemContainer(item_id=self.ui_item_counter, client_data=client_info)
                self.all_items_map[new_item.item_id] = new_item
                
                current_row = self.get_current_row_for_add()

                if current_row is None or len(current_row.children) >= MAX_ITEMS_PER_ROW:
                    current_row = self.add_new_row_for_add()
                
                await current_row.mount(new_item)
                
                content_area = self.query_one("#content_area", VerticalScroll)
                content_area.scroll_end(animate=True, speed=150)
            else:
                self.notify("Todos los clientes han sido agregados.", title="Información")


    async def _remove_item_widget_from_dom(self, item_to_remove: ItemContainer) -> None:
        await item_to_remove.remove()

    async def _reflow_all_items(self) -> None:
        content_area = self.query_one("#content_area", VerticalScroll)
        items_to_remount = list(self.all_items_map.values())
        # Opcional: ordenar por el ui_item_counter si se desea mantener un orden visual consistente
        # items_to_remount.sort(key=lambda item: item.item_id) 

        current_rows = content_area.query(".row_container").filter("Horizontal")
        for row in current_rows:
            await row.remove()

        current_row_for_reflow: Horizontal | None = None
        for item_widget in items_to_remount:
            if current_row_for_reflow is None or len(current_row_for_reflow.children) >= MAX_ITEMS_PER_ROW:
                current_row_for_reflow = Horizontal()
                current_row_for_reflow.add_class("row_container")
                await content_area.mount(current_row_for_reflow) 
            
            await current_row_for_reflow.mount(item_widget)

        if items_to_remount:
            content_area.scroll_end(animate=True, speed=150)


    async def on_item_container_remove_item(self, message: ItemContainer.RemoveItem) -> None:
        item_to_remove = message.item_to_remove
        item_id_removed = item_to_remove.item_id

        if item_id_removed in self.all_items_map:
            await self._remove_item_widget_from_dom(item_to_remove)
            del self.all_items_map[item_id_removed]
            await self._reflow_all_items()
            
            # Nota: self.client_idx_to_add no se decrementa. Si eliminas un cliente
            # y luego agregas, se agregará el *siguiente* cliente no mostrado de la lista original.
            self.notify(f"Cliente '{item_to_remove.client_data.get('name', item_id_removed)}' eliminado. Contenedores reorganizados.", title="Información")
        else:
            self.notify(f"Intento de eliminar el item {item_id_removed} que no estaba en el mapa.", severity="warning")

if __name__ == "__main__":
    # Asegúrate de que el archivo wg0.json esté en el mismo directorio que este script,
    # o ajusta la constante CLIENT_DATA_FILE.
    app = DynamicContainerApp()
    app.run()
