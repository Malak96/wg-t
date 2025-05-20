from textual import containers
# Importar la clase principal de la aplicación y el tipo ComposeResult
from textual.app import App, ComposeResult

# Importar los contenedores para organizar el layout
from textual.containers import Container, Vertical, Horizontal, Grid

# Importar los widgets básicos para la UI
from textual.widgets import Button, ListView, ListItem, Label, Input, Static

import json
file_path = "wg_data.json"
class TerminalUI(App):
    """A Textual app for managing instances and clients."""

    # Define the CSS for the app
    CSS = """
    Horizontal {
        width: 100%;
    }
    .left-panel {
        width: 30;      /* Fija el ancho a 20 columnas */
        min-width: 30;  /* No permite que sea menor */
        max-width: 30;  /* No permite que sea mayor */
        padding: 1;
        padding-left: 2;
        box-sizing: border-box; 
    }
    .right-panel {
        width: 62%;
        padding: 1;
        padding-right: 2;
        box-sizing: border-box;
    }
    .button-row {
        width: 100%;
        height: 3;
        padding: 0;
        margin: 0;
    }
    .list-btn {
        width: 1fr;
        height: 3;
        min-width: 0;
        text-align: center;
        padding: 0;
        margin: 0;
    }
    .list-view {
        overflow: auto;    /* Permite scroll si el texto es largo */
        width: 1fr;       /* Ocupa todo el ancho disponible */
        height: 1fr;
        min-height: 5;
        margin: 0 0;  
        background: $panel; 
        /* border: round #666; */
        margin-bottom: 1;
        box-sizing: border-box;
    }
    /* Renombrar .details-grid a .details-container para claridad */
    .details-container {
        padding: 0 1;      /* Padding interno: 0 arriba/abajo, 1 a los lados */
        margin: 1 1 1 1;   /* Margen: 1 arriba, 0 derecha, 0 abajo, 1 izquierda (para separar de left-panel) */
        border: round $panel; /* Borde Blanco */
        height: auto;      /* Se ajusta a la altura de su contenido */
    }

    /* Estilo para los Horizontals dentro del contenedor de detalles para compactarlos */
    .details-container Horizontal {
        height: 1;         /* Hace cada fila de detalle compacta verticalmente */
    }

    .field-label {
        text-style: bold;
        padding: 0 1 0 0;  /* Padding: 0 top, 1 right, 0 bottom, 0 left */
        text-align: left;
        width: auto;       /* Se ajusta al contenido del label */
        max-width: 12;     /* Limita el ancho máximo (ej. "PrivKey:" o "Endpoint:") */
        height: 1;         /* Asegurar altura 1 */
    }
    .value-label {
        /* text-style: bold; */ /* Opcional, quitar si se ve muy cargado */
        padding: 0;        /* Sin padding extra, field-label ya da separación a su derecha */
        text-align: left;
        width: 1fr;        /* Ocupa el resto del espacio en el Horizontal */
        height: 1;         /* Asegurar altura 1 */
    }
    Button#btn_generate {
        width: auto;
        margin-top: 1;
    }
    .ListHorizontal {
        width: 100%; /* Make the main horizontal container take full width */
        height: 1; /* Make the main horizontal container take full height */
        text-style: bold;
    }
    .port_label {
        align: center right;
    }
    """

    async def refresh_instances_list(self):
        """Actualiza el ListView de instancias según wg_data."""
        list_instances = self.query_one("#list_instances", ListView)
        list_instances.clear()
        # Asegúrate de iterar sobre los servidores, no sobre el diccionario raíz
        for name, instance in self.wg_data["servres"].items():
            item = ListItem(
                Horizontal(Label(instance["name"]),Label(str(instance["port"])),classes="ListHorizontal"),id=f"srv_{name}")
            
            await list_instances.append(item)

    async def on_mount(self) -> None:
        """Carga datos y refresca la lista al iniciar."""
        self.load_wg_data_from_json("wg_data.json")
        await self.refresh_instances_list()

    def load_wg_data_from_json(self, file_path):
        """Carga wg_data desde un archivo JSON."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Si tu JSON tiene la clave "servres", usa esa parte
            self.wg_data = data.get("servrs", data)

    async def update_data_and_refresh(self, file_path):
        """Carga datos y refresca la lista."""
        self.load_wg_data_from_json(file_path)
        await self.refresh_instances_list()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected_id = event.item.id
        real_id = selected_id.replace("srv_", "")
        instance = self.wg_data["servres"][real_id]
    # ...actualiza los labels como antes...
        # Actualiza los inputs
        self.query_one("#input_pubkey", Label).update(instance.get("publicKey", ""))
        self.query_one("#input_privkey", Label).update(instance.get("privateKey", ""))
        self.query_one("#input_address", Label).update(instance.get("address", ""))
        self.query_one("#input_port", Label).update(str(instance.get("port", "")))
        self.query_one("#input_dns", Label).update(instance.get("dns", ""))
        self.query_one("#input_endpoint", Label).update(instance.get("endpoint", ""))

    def compose(self) -> ComposeResult:
        """Compose the layout of the app."""
        yield Horizontal(
            Vertical(
                Label("Instancias"),
                ListView(
                    id="list_instances",
                    classes="list-view"
                ),
                Label("Clientes"),
                ListView(
                    id="list_clients",
                    classes="list-view"
                ),
                Horizontal(
                    Button("Nuevo", id="btn_edit_client", classes="list-btn"),
                    Button("Eliminar", id="btn_delete_client", classes="list-btn",variant="error"),
                    classes="button-row"
                ),
                classes="left-panel"
            ),
            # Right panel: Contains details and generate button
           # with container.Grid():
            #    yield Horizontal(Label("PubKey:", classes="field-label"), Label(id="input_pubkey", classes="value-label"))
                
                
            
            Vertical(
                Label("Detalles"),
                Vertical(
                Horizontal(Label("PubKey:", classes="field-label"), Label(id="input_pubkey", classes="value-label")),
                Horizontal(Label("PrivKey:", classes="field-label"), Label(id="input_privkey", classes="value-label")),
                Horizontal(Label("Address:", classes="field-label"), Label(id="input_address", classes="value-label")),
                Horizontal(Label("Puerto:", classes="field-label"), Label(id="input_port", classes="value-label")),
                Horizontal(Label("DNS:", classes="field-label"), Label(id="input_dns", classes="value-label")),
                Horizontal(Label("Endpoint:", classes="field-label"), Label(id="input_endpoint", classes="value-label")),
                classes="details-container") # Cambiado de details-grid
            )
            
        )

# Run the app
if __name__ == "__main__":
    app = TerminalUI()
    app.run()
