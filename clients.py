from textual import  on 
# Importar la clase principal de la aplicación y el tipo ComposeResult
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
# Importar los contenedores para organizar el layout
from textual.containers import Vertical, Horizontal

# Importar los widgets básicos para la UI
from textual.widgets import Button, Label, Input, Static, Select

import json
import ipaddress

import works

class Add_edit_client(ModalScreen):
    """A widget to edit a client."""
    def __init__(self, id_server: str, id_client: str, app_ref, verify: bool, previous_screen: None) -> None:
        self.previous_screen = previous_screen
        self.id_server = id_server
        self.id_client = id_client
        self.app_ref = app_ref
        self.verify = verify
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
                Button("Generar", id="btn_gen_key", variant="default", classes="edit_client_keys")
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
                Input(id="input_persistent_keepalive",placeholder="24", classes="input_edit_client")
            ),
            Horizontal(
                Label("allowedIPs:", classes="label_edit_client"),
                Input(id="input_allowed_ips",placeholder=" 0.0.0.0/0, ::/0", classes="input_edit_client"),
                Label("Habilitado:", classes="label_edit_client"),
                Select([("Sí", True), ("No", False)], allow_blank=False, id="select_enabled")
            ),
            Horizontal(
                Button("Guardar",id="btn_save_client",variant="primary",classes="list-btn"),
                Button("Cancelar",id="btn_cancel_client", variant="error", classes="list-btn"),
                classes="list-btn"
            )
            ,id="Add_edit_client"
        )

    async def _on_mount(self) -> None:
        """Método para manejar el evento de montaje."""
        await self.load_client_data()  # Cargar datos del cliente al montar

    async def load_client_data(self):
        if self.verify == True:
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
        else:
            server_data = self.app_ref.wg_data.get("servers", {}).get(self.id_server, {})
            clients = server_data.get("clients",{})
            new_address_client = self.get_next_available_ip("",server_data.get("address",{}))
            self.gen_keys(False)  # Generar claves si no se está editando un cliente existente
            self.gen_keys(True)
            ##self.query_one("#name_client", Input).value = valor.get("name", "") or ""
            self.query_one("#input_client_address", Input).placeholder = new_address_client
            self.query_one("#input_dns", Input).placeholder = server_data.get("dns", "") or ""
            

            
            
    def gen_keys(self, key_type: bool ) -> None:
        self.key_type = key_type
        if key_type == True:
            """Genera una clave precompartida y la muestra en el campo correspondiente."""
            psk = works.generate_preshared_key()
            self.query_one("#input_preshared_key", Input).value = psk
        elif key_type == False:
            priv_key, pub_key = works.generate_keys()
            self.query_one("#input_private_key", Input).value = priv_key
            self.query_one("#input_public_key", Input).value = pub_key
        
    @on(Button.Pressed, "#btn_gen_key")
    def btn_gen_key(self, event: Button.Pressed) -> None:
        """Generar claves y mostrarlas en los campos correspondientes."""
        self.gen_keys(False)
        
    @on(Button.Pressed, "#btn_show_preshared_key")
    def btn_show_preshared_key(self, event: Button.Pressed) -> None:
        """Generar una clave precompartida y mostrarla en el campo correspondiente."""
        self.gen_keys(True)
        

        
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
    
    def get_next_available_ip(self, clients_data, server_address):
        """Obtiene la siguiente dirección IP disponible en la subred especificada por el servidor."""
        try:
            # Crear el objeto de red a partir de la dirección del servidor
            network = ipaddress.ip_network(server_address, strict=False)
            server_ip = ipaddress.ip_address(server_address.split('/')[0])  # Extraer solo la IP del servidor
        except ValueError:
            self.notify (f"[bold red]Error:[/bold red] No se pudo generar una ip de forma automatica para este cliente a partir de la ip del del seridor: {server_address}",
                         title="Dirección del servidor inválida", severity="warning")
            return None
        used_ips = set()
        if clients_data:
            for client_details in clients_data.values():
                client_address = client_details.get("address")
                if client_address:
                    try:
                        ip = ipaddress.ip_address(client_address.split('/')[0])  # Extraer solo la IP
                        used_ips.add(ip)
                    except ValueError:
                        return ""
                        #self.notify(f"[yellow]Advertencia:[/yellow] Dirección IP inválida: {client_address}",severity="warning")
                        
        # Iterar sobre todas las IPs posibles en la subred, excluyendo la del servidor
        for ip in network.hosts():
            if ip != server_ip and ip not in used_ips:
                return f"{ip}/32"  # Devuelve la IP con máscara /32

        return ""  # No hay IPs disponibles