from textual import  on 
# Importar la clase principal de la aplicación y el tipo ComposeResult
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
# Importar los contenedores para organizar el layout
from textual.containers import Vertical, Horizontal
from textual.suggester import SuggestFromList


# Importar los widgets básicos para la UI
from textual.widgets import Button, Label, Input, Static, Select
#import uuid
import json

import works
# DNS públicas más conocidas y seguras
dns_servers = [
    "1.1.1.1",       # Cloudflare DNS (rápido y privado)
    "1.0.0.1",       # Cloudflare DNS (secundario)
    "9.9.9.9",       # Quad9 (filtrado de malware)
    "149.112.112.112", # Quad9 (secundario)
    "8.8.8.8",       # Google DNS
    "8.8.4.4",       # Google DNS (secundario)
    "208.67.222.222", # OpenDNS (Cisco)
    "208.67.220.220", # OpenDNS (secundario)
    "94.140.14.14",  # AdGuard DNS (bloqueo de publicidad)
    "94.140.15.15",  # AdGuard DNS (secundario)
    "76.76.2.0",     # Control D (configurable, por defecto sin bloqueo)
    "76.76.10.0",    # Control D (secundario)
    "185.228.168.9", # CleanBrowsing (Family Filter)
    "185.228.169.9"  # CleanBrowsing (secundario)
]


class Add_edit_server(ModalScreen):
    """A widget to edit a client."""
    def __init__(self, id_server: str, new_server: bool, previous_screen: None) -> None:
        self.previous_screen = previous_screen
        self.id_server = id_server
        self.new_server = new_server
        
        
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
                Label("PostUp:", classes="label_edit_client"),
                Input(id="PostUp", classes="input_edit_client",value="iptables -t nat -A POSTROUTING -s $address$ -o eth0 -j MASQUERADE; iptables -A INPUT -p udp -m udp --dport 64625 -j ACCEPT; iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT;"),
            ),
            Horizontal(
                Label("PostDown:", classes="label_edit_client"),
                Input(id="PostDown", classes="input_edit_client"),
            ),
            Horizontal(
                Label("name:", classes="label_edit_client"),
                Input(id="name", classes="input_edit_client"),
                Label("address:", classes="label_edit_client"),
                Input(id="input_address", classes="input_edit_client")),
          
            Horizontal(
                Label("endpoint:", classes="label_edit_client"),
                Input(id="endpoint", classes="input_edit_client"),
                Label("port:", classes="label_edit_client"),
                Input(id="port", classes="input_edit_client")
            ),
            Horizontal(
                Label("DNS:", classes="label_edit_client"),
                Input(id="input_dns", classes="input_edit_client",suggester=SuggestFromList(dns_servers)),
                Label("Habilitado:", classes="label_edit_client"),
                Select([("Sí", True), ("No", False)], allow_blank=False, id="select_enabled")
            ),
            Horizontal(
                Button("Guardar",id="btn_save",variant="primary",classes="list-btn"),
                Button("Cancelar",id="btn_cancel", variant="error", classes="list-btn"),
                classes="list-btn"
            )
            ,id="Add_edit_server"
        )

    async def _on_mount(self) -> None:

        await self.load_client_server()  # Cargar datos del cliente al montar

    async def load_client_server(self):
        if self.new_server == False:
            """Carga los datos del server."""
            valor = self.previous_screen.wg_data.get("servers", {}).get(self.id_server, {})
            self.query_one("#name", Input).value = valor.get("name", "") or ""
            self.query_one("#input_address", Input).value = valor.get("address", "") or ""
            self.query_one("#input_private_key", Input).value = valor.get("privateKey", "") or ""
            self.query_one("#input_public_key", Input).value = valor.get("publicKey", "") or ""
            self.query_one("#input_dns", Input).value = valor.get("dns", "") or ""
            self.query_one("#select_enabled", Select).value = valor.get("enabled", False)
        else:
            priv_key, pub_key = works.generate_keys()
            self.query_one("#input_private_key", Input).value = priv_key
            self.query_one("#input_public_key", Input).value = pub_key

        
    @on(Button.Pressed, "#btn_gen_key")
    def btn_gen_key(self, event: Button.Pressed) -> None:
        self.gen_keys(False)
 
    @on(Button.Pressed, "#btn_cancel")
    def cancelar(self, event: Button.Pressed) -> None:
        if self.new_server==True:
            print("x")
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
        if self.query_one("#input_address", Input).value == "" or self.query_one("#port",Input).value == "" or self.query_one("#endpoint", Input).value == "" or self.query_one("#input_private_key", Input).value == "" or self.query_one("#input_public_key", Input).value == "":
            self.notify("Los siguientes camposs no pueden quedar vacios: \n - privateKey\n - publicKey\n - address\n - port\n - dns\n - endpoint",severity="warning")
            return
        if self.save_data():
            await self.previous_screen.refresh_server_select()
            self.notify(f"Se guardo correctamente la configutacion de {self.query_one("#name", Input).value}",severity="information",title="Guardado")
            self.app.pop_screen()  # Cerrar la pantalla actual
        else:
            self.notify("Ocurrio un error al guardar los datos no se guardo la configuracion.",severity="error",title="Error")
        
    def save_data(self):
        try:
            server_new={
                "name":self.query_one("#name", Input).value,
                "privateKey":self.query_one("#input_private_key", Input).value,
                "publicKey":self.query_one("#input_public_key", Input).value,
                "address":self.query_one("#input_address", Input).value,
                "port": self.query_one("#port",Input).value,
                "dns":self.query_one("#input_dns", Input).value ,
                "endpoint":self.query_one("#endpoint", Input).value,
                "enable":self.query_one("#select_enabled", Select).value
                }
            self.previous_screen.wg_data["servers"][self.id_server] = server_new
        
            with open("wg_data.json", 'w', encoding='utf-8') as f:
                json.dump(self.previous_screen.wg_data, f, indent=2, ensure_ascii=False)
            return True # Indicar éxito
        except Exception as e:
            return False
            
        


        
    