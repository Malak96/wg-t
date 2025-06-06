from textual import  on 
# Importar la clase principal de la aplicación y el tipo ComposeResult
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
# Importar los contenedores para organizar el layout
from textual.containers import Vertical, Horizontal

# Importar los widgets básicos para la UI
from textual.widgets import Button, Label, Input, Select, Switch

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
                Switch(id="pshk_switch", value= True)
                #Button("⟳", id="btn_show_preshared_key", variant="primary", classes="edit_client_keys")
            ),
            Horizontal(
                Label("name:", classes="label_edit_client"),
                Input(id="name", classes="input_edit_client"),
                Label("address:", classes="label_edit_client"),
                Input(id="input_address", classes="input_edit_client")),
          
            Horizontal(
                Label("DNS:", classes="label_edit_client"),
                Input(id="input_dns", classes="input_edit_client"),
                Label("Keepalive:", classes="label_edit_client"),
                Input(id="input_persistent_keepalive",value="0", classes="input_edit_client")
            ),
            Horizontal(
                Label("allowedIPs:", classes="label_edit_client"),
                Input(id="input_allowed_ips",value=" 0.0.0.0/0, ::/0", classes="input_edit_client"),
                Label("Habilitado:", classes="label_edit_client"),
                Select([("Sí", True), ("No", False)], allow_blank=False, id="select_enabled")
            ),
            Horizontal(
                Button("Guardar",id="btn_save",variant="primary",classes="list-btn"),
                Button("Cancelar",id="btn_cancel", variant="error", classes="list-btn"),
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
            self.query_one("#name", Input).value = valor.get("name", "") or ""
            self.query_one("#input_address", Input).value = valor.get("address", "") or ""
            self.query_one("#input_private_key", Input).value = valor.get("privateKey", "") or ""
            self.query_one("#input_public_key", Input).value = valor.get("publicKey", "") or ""
            if valor.get("presharedKey",False):
                self.query_one("#input_preshared_key", Input).value = valor.get("presharedKey")
                self.query_one("#input_preshared_key", Input).disabled = False
                self.query_one("#pshk_switch",Switch).value = True
            else:
                self.query_one("#input_preshared_key", Input).value = ""
                self.query_one("#input_preshared_key", Input).disabled = True
                self.query_one("#pshk_switch",Switch).value = False
            self.query_one("#input_dns", Input).value = valor.get("dns", "") or ""
            self.query_one("#input_persistent_keepalive", Input).value = str(valor.get("persistentKeepalive", "")) or ""
            self.query_one("#input_allowed_ips", Input).value = valor.get("allowedIPs", "") or ""
            self.query_one("#select_enabled", Select).value = valor.get("enable", False)
        else:
            # Si es un nuevo cliente, se generan claves y se obtiene una dirección IP disponible.
            server_data = self.app_ref.wg_data.get("servers").get(self.id_server)
            cliens_data = self.app_ref.wg_data.get("servers").get(self.id_server).get("clients",{})
            #clients = server_data.get("clients",{})
            new_address_client = self.get_next_available_ip(cliens_data,server_data.get("address",{}))
            #Genera una clave precompartida y la muestra en el campo correspondiente.
            psk = works.generate_preshared_key()
            priv_key, pub_key = works.generate_keys()
            self.query_one("#input_private_key", Input).value = priv_key
            self.query_one("#input_public_key", Input).value = pub_key
            self.query_one("#input_preshared_key", Input).value = psk
            self.query_one("#input_address", Input).value = new_address_client
            self.query_one("#input_dns", Input).value = server_data.get("dns", "") or ""
    @on(Switch.Changed, "#pshk_switch")
    def pshk_switch(self, event:Switch.Changed) -> None:
        if self.query_one("#pshk_switch",Switch).value:
            self.query_one("#input_preshared_key", Input).disabled = False
            psk = works.generate_preshared_key()
            self.query_one("#input_preshared_key", Input).value = psk
        else:
            self.query_one("#input_preshared_key", Input).value = ""
            self.query_one("#input_preshared_key", Input).disabled = True
            

          
    @on(Button.Pressed, "#btn_gen_key")
    def btn_gen_key(self, event: Button.Pressed) -> None:
        """Generar claves y mostrarlas en los campos correspondientes."""
        priv_key, pub_key = works.generate_keys()
        self.query_one("#input_private_key", Input).value = priv_key
        self.query_one("#input_public_key", Input).value = pub_key
        
    @on(Button.Pressed, "#btn_show_preshared_key")
    def btn_show_preshared_key(self, event: Button.Pressed) -> None:
        """Generar una clave precompartida y mostrarla en el campo correspondiente."""
        psk = works.generate_preshared_key()
        self.query_one("#input_preshared_key", Input).value = psk
        
    @on(Button.Pressed, "#btn_cancel")
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
            
    @on(Button.Pressed, "#btn_save")
    async def btn_save_handler(self, event: Button.Pressed) -> None:
        if self.query_one("#name", Input).value == "":
            self.notify("Debe proporcionar un nombre para el servidor.",severity="information")
            return
        #if self.query_one("#input_address", Input).value == "" or self.query_one("#port",Input).value == "" or self.query_one("#endpoint", Input).value == "" or self.query_one("#input_private_key", Input).value == "" or self.query_one("#input_public_key", Input).value == "":
        #    self.notify("Los siguientes camposs no pueden quedar vacios: \n - privateKey\n - publicKey\n - address\n - port\n - dns\n - endpoint",severity="warning")
        #    return
        if self.save_data():
            await self.app_ref.refresh_server_select()
            self.notify(f"Se guardo correctamente la configutacion de {self.query_one("#name", Input).value}",severity="information",title="Guardado")
            self.app.pop_screen()  # Cerrar la pantalla actual
        else:
            self.notify(f"[bold red]Error:[/bold red] Ocurrió un error al guardar los datos: {str(e)}",
                         title="Error al guardar", severity="error")
        
    def save_data(self):
        try:
            client_new={
                "name":self.query_one("#name", Input).value,
                "privateKey":self.query_one("#input_private_key", Input).value,
                "publicKey":self.query_one("#input_public_key", Input).value,
                "presharedKey":self.query_one("#input_preshared_key", Input).value,
                "persistentKeepalive":self.query_one("#input_persistent_keepalive", Input).value or 0,
                "address":self.query_one("#input_address", Input).value,
                "dns":self.query_one("#input_dns", Input).value,
                "allowedIPs":self.query_one("#input_allowed_ips", Input).value,
                "enable":self.query_one("#select_enabled", Select).value
                }
            if "clients" not in self.app_ref.wg_data["servers"][self.id_server]:
                self.app_ref.wg_data["servers"][self.id_server]["clients"]={}
            self.app_ref.wg_data["servers"][self.id_server]["clients"][self.id_client] = client_new
        
            with open("wg_data.json", 'w', encoding='utf-8') as f:
                json.dump(self.app_ref.wg_data, f, indent=2, ensure_ascii=False)
            return True # Indicar éxito
        except Exception as e:
            return False
            
    
    def get_next_available_ip(self, clients_data, server_address):
        """Obtiene la siguiente dirección IP disponible en la subred especificada por el servidor."""
        try:
            # Crear el objeto de red a partir de la dirección del servidor
            network = ipaddress.ip_network(server_address, strict=False)
            server_ip = ipaddress.ip_address(server_address.split('/')[0])  # Extraer solo la IP del servidor
        except ValueError:
            self.notify (f"[bold red]Error:[/bold red] No se pudo generar una ip de forma automatica para este cliente a partir de la ip del del seridor: {server_address}",
                         title="Dirección del servidor inválida", severity="warning")
            self.app.pop_screen()
            return "0.0.0.0/32"
        used_ips = set()
        if clients_data:
            for client_details in clients_data.values():
                client_address = client_details.get("address")
                if client_address:
                    try:
                        ip = ipaddress.ip_address(client_address.split('/')[0])  # Extraer solo la IP
                        used_ips.add(ip)
                    except ValueError:
                        self.notify(f"[bold red]Error:[/bold red] Dirección IP inválida del cliente: {client_address}",
                                    title="Dirección IP inválida", severity="warning")
                        self.app.pop_screen()
                        return "0.0.0.0/32"  # Retornar una IP inválida si hay un error en la dirección del cliente
                        #self.notify(f"[yellow]Advertencia:[/yellow] Dirección IP inválida: {client_address}",severity="warning")
                        
        # Iterar sobre todas las IPs posibles en la subred, excluyendo la del servidor
        for ip in network.hosts():
            if ip != server_ip and ip not in used_ips:
                return f"{ip}/32"  # Devuelve la IP con máscara /32
        self.notify(f"[bold red]Error:[/bold red] No hay direcciones IP disponibles en la subred {server_address}",
                    title="Sin IPs disponibles", severity="warning")
        self.app.pop_screen()
        return "0.0.0.0/32"  # No hay IPs disponibles