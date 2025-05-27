import json
import os
import uuid
import datetime
import subprocess
import sys
import ipaddress

try:
    from rich.console import Console
    from rich.table import Table
    from rich.box import HEAVY_HEAD # Cambiado de ROUNDED para el estilo de tabla deseado
    from rich.text import Text     # Añadido para formateo de texto en la tabla
    from rich.prompt import Prompt, Confirm # <-- AÑADIDO Confirm
    from rich.panel import Panel   # Añadido para mejorar la presentación de mensajes
except ImportError:
    print("La biblioteca 'rich' no está instalada. Por favor, instálala con: pip install rich")
    sys.exit(1)

console = Console()

WG_CONFIG_FILE = "wg_data.json"
IP_SUBNET_PREFIX_DEFAULT = "10.10.10.1/24" # Fallback si no se puede derivar del servidor
IP_START_OCTET = 2
IP_MAX_OCTET = 254

def load_data(file_path):
    """Carga los datos desde el archivo JSON. Si el archivo no existe o es ilegible, muestra un error."""
    if not os.path.exists(file_path):
        console.print(Panel(f"[bold red]Error:[/bold red] El archivo '{file_path}' no existe.", border_style="red"))
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        console.print(Panel(f"[bold red]Error:[/bold red] El archivo '{file_path}' no contiene un JSON válido o está dañado.", border_style="red"))
        return None
    except Exception as e:
        console.print(Panel(f"[bold red]Ocurrió un error inesperado al cargar '{file_path}':[/bold red] {e}", border_style="red"))
        return None

def save_data(file_path, data):
    """Guarda los datos en el archivo JSON con formato indentado."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(Panel(f"[green]Datos guardados exitosamente en '{file_path}'.[/green]", border_style="green"))
        return True # Indicar éxito
    except Exception as e:
        console.print(Panel(f"[bold red]Error al guardar los datos en '{file_path}':[/bold red] {e}", border_style="red"))
        return False # Indicar fallo

def generate_wg_keys():
    """Genera un par de claves privada y pública de WireGuard usando el comando 'wg'."""
    try:
        # Generar clave privada
        priv_key_proc = subprocess.run(['wg', 'genkey'], capture_output=True, text=True, check=True, encoding='utf-8')
        private_key = priv_key_proc.stdout.strip()

        # Generar clave pública desde la privada
        pub_key_proc = subprocess.run(['wg', 'pubkey'], input=private_key, capture_output=True, text=True, check=True, encoding='utf-8')
        public_key = pub_key_proc.stdout.strip()
        
        return private_key, public_key
    except FileNotFoundError:
        console.print("[bold yellow]Advertencia:[/bold yellow] Comando 'wg' no encontrado. Usando placeholders para las claves.")
        console.print("Por favor, asegúrate de que las herramientas de WireGuard estén instaladas y en el PATH para generar claves reales.")
        return "PLACEHOLDER_PRIVATE_KEY_wg_not_found", "PLACEHOLDER_PUBLIC_KEY_wg_not_found"
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error ejecutando el comando 'wg':[/bold red] {e}")
        console.print("[yellow]Usando placeholders para las claves.[/yellow]")
        return "PLACEHOLDER_PRIVATE_KEY_wg_error", "PLACEHOLDER_PUBLIC_KEY_wg_error"

def generate_preshared_key():
    """Genera una clave precompartida (PresharedKey) de WireGuard usando 'wg genpsk'."""
    try:
        psk_proc = subprocess.run(['wg', 'genpsk'], capture_output=True, text=True, check=True, encoding='utf-8')
        return psk_proc.stdout.strip()
    except FileNotFoundError:
        console.print("[bold yellow]Advertencia:[/bold yellow] Comando 'wg' no encontrado. No se pudo generar PresharedKey.")
        console.print("Por favor, asegúrate de que las herramientas de WireGuard estén instaladas y en el PATH.")
        return None
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error ejecutando 'wg genpsk':[/bold red] {e}")
        return None

def get_next_available_ip(clients_data, server_address):
    """Obtiene la siguiente dirección IP disponible en la subred especificada por el servidor."""
    try:
        # Crear el objeto de red a partir de la dirección del servidor
        network = ipaddress.ip_network(server_address, strict=False)
        server_ip = ipaddress.ip_address(server_address.split('/')[0])  # Extraer solo la IP del servidor
    except ValueError:
        console.print(Panel(f"[bold red]Error:[/bold red] Dirección del servidor inválida: {server_address}", border_style="red"))
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
                    console.print(Panel(f"[yellow]Advertencia:[/yellow] Dirección IP inválida: {client_address}", border_style="yellow"))

    # Iterar sobre todas las IPs posibles en la subred, excluyendo la del servidor
    for ip in network.hosts():
        if ip != server_ip and ip not in used_ips:
            return f"{ip}/32"  # Devuelve la IP con máscara /32

    return None  # No hay IPs disponibles

def add_new_client(client_name, server_id):
    """
    Genera un nuevo cliente, lo añade a los datos cargados y guarda el archivo.
    server_id: el id del servidor al que se agregará el cliente
    """
    if not client_name or not client_name.strip():
        console.print(Panel("[bold red]Error:[/bold red] El nombre del cliente no puede estar vacío.", border_style="red"))
        return

    config_data = load_data(WG_CONFIG_FILE)
    if not config_data:
        console.print(Panel("[bold red]Error:[/bold red] No se pudo cargar la configuración. Operación cancelada.", border_style="red"))
        return

    if "servers" not in config_data or server_id not in config_data["servers"]:
        console.print(Panel(f"[bold red]Error:[/bold red] El servidor '{server_id}' no existe.", border_style="red"))
        return

    server_config = config_data["servers"][server_id]
    if "clients" not in server_config or not isinstance(server_config["clients"], dict):
        server_config["clients"] = {}

    server_address_from_config = server_config.get("address")
    if not server_address_from_config:
        console.print(Panel(f"[bold red]Error:[/bold red] 'address' del servidor no encontrada o vacía. No se puede generar una dirección IP para el cliente.", border_style="red"))
        return

    client_uuid = str(uuid.uuid4())
    private_key, public_key = generate_wg_keys()
    next_ip = get_next_available_ip(server_config.get("clients"), server_address_from_config)
    if not next_ip:
        console.print(Panel(f"[bold red]Error:[/bold red] No hay direcciones IP disponibles en la subred derivada de {server_address_from_config}.", border_style="red"))
        return

    timestamp = datetime.datetime.utcnow().isoformat(timespec='milliseconds') + "Z"
    server_dns_config = server_config.get("dns")
    client_dns_to_set = server_dns_config if isinstance(server_dns_config, str) else None
    preshared_key_to_set = None
    generate_psk_str = server_config.get("PresharedKey", "False")
    if str(generate_psk_str).lower() == "true":
        preshared_key_to_set = generate_preshared_key()
    persistent_keepalive_default = 0
    persistent_keepalive_to_set = server_config.get("persistentKeepalive", persistent_keepalive_default)
    if not isinstance(persistent_keepalive_to_set, int) or persistent_keepalive_to_set < 0:
        persistent_keepalive_to_set = persistent_keepalive_default

    new_client_data = {
        "id": client_uuid,
        "name": client_name.strip(),
        "address": next_ip,
        "privateKey": private_key,
        "publicKey": public_key,
        "PresharedKey": preshared_key_to_set,
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "dns": client_dns_to_set,
        "persistentKeepalive": persistent_keepalive_to_set,
        "allowedIPs": "0.0.0.0/0, ::/0",
        "enabled": True
    }
    server_config["clients"][client_uuid] = new_client_data
    if save_data(WG_CONFIG_FILE, config_data):
        console.print(Panel(f"[green]Cliente '{client_name}' añadido exitosamente al servidor '{server_id}'.[/green]", border_style="green"))
        console.print("\n[bold green]Cliente añadido y guardado. Detalles:[/bold green]")
        details_table = Table(show_header=True, header_style="bold magenta", box=HEAVY_HEAD)
        details_table.add_column("Campo", style="cyan", no_wrap=True, min_width=25)
        details_table.add_column("Valor", style="white", min_width=40)

        for key, value in new_client_data.items():
            display_value = str(value) if value is not None else Text("No establecido", style="italic dim")
            formatted_key_display = key.replace('_', ' ').capitalize()
            details_table.add_row(formatted_key_display, display_value)

        console.print(details_table)
        Prompt.ask("[dim]Presiona Enter para continuar...[/dim]", default="", show_default=False)
    else:
        console.print(Panel("[bold red]Error al guardar los datos del cliente. No se mostrarán los detalles en tabla.[/bold red]", border_style="red"))

# Nueva función para agregar un servidor

def add_new_server(server_id, server_data):
    config_data = load_data(WG_CONFIG_FILE)
    if not config_data:
        config_data = {"servers": {}}
    if "servers" not in config_data:
        config_data["servers"] = {}
    if server_id in config_data["servers"]:
        console.print(Panel(f"[red]El servidor '{server_id}' ya existe.[/red]", border_style="red"))
        return
    server_data["clients"] = {}
    config_data["servers"][server_id] = server_data
    if save_data(WG_CONFIG_FILE, config_data):
        console.print(Panel(f"[green]Servidor '{server_id}' añadido exitosamente.[/green]", border_style="green"))
    else:
        console.print(Panel(f"[red]No se pudo guardar el servidor en el archivo.[/red]", border_style="red"))

if __name__ == "__main__":
    console.rule("[bold blue]Añadir Nuevo Cliente WireGuard[/bold blue]")
    server_id = console.input("[b]Introduce el ID del servidor al que añadir el cliente:[/b] ")
    client_name_input = console.input("[b]Introduce el nombre para el nuevo cliente:[/b] ")
    if client_name_input and server_id:
        add_new_client(client_name_input, server_id)
    else:
        console.print("[yellow]Operación cancelada. No se añadió ningún cliente.[/yellow]")

    # Opción para agregar un nuevo servidor
    if Confirm.ask("¿Deseas agregar un nuevo servidor?", default=False):
        new_server_id = console.input("[b]Introduce el ID para el nuevo servidor:[/b] ")
        address = console.input("Dirección IP/máscara del servidor: ")
        dns = console.input("DNS del servidor: ")
        port = console.input("Puerto del servidor: ")
        endpoint = console.input("Endpoint del servidor: ")
        persistent_keepalive = console.input("PersistentKeepalive (0 para desactivar): ")
        interface = console.input("Nombre de la interfaz: ")
        preshared = Confirm.ask("¿Habilitar PresharedKey?", default=True)
        server_data = {
            "name": new_server_id,
            "privateKey": "",
            "publicKey": "",
            "address": address,
            "dns": dns,
            "port": int(port),
            "PresharedKey": str(preshared),
            "endpoint": endpoint,
            "persistentKeepalive": int(persistent_keepalive),
            "interface": interface
        }
        add_new_server(new_server_id, server_data)