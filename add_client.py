import json
import os
import uuid
import datetime
import subprocess
import sys

try:
    from rich.console import Console
    from rich.table import Table
    from rich.box import HEAVY_HEAD # Cambiado de ROUNDED para el estilo de tabla deseado
    from rich.text import Text     # Añadido para formateo de texto en la tabla
except ImportError:
    print("La biblioteca 'rich' no está instalada. Por favor, instálala con: pip install rich")
    sys.exit(1)

console = Console()

WG_CONFIG_FILE = "wg0.json"
IP_SUBNET_PREFIX_DEFAULT = "10.10.10.1/24" # Fallback si no se puede derivar del servidor
IP_START_OCTET = 2
IP_MAX_OCTET = 254

def load_data(file_path):
    """Carga los datos desde el archivo JSON. Si el archivo no existe, devuelve una estructura base."""
    if not os.path.exists(file_path):
        console.print(f"[yellow]El archivo '{file_path}' no existe. Se creará uno nuevo con estructura base.[/yellow]")
        # Nueva estructura base con "server"
        return {
            "server": {
                "address": IP_SUBNET_PREFIX_DEFAULT, # e.g., "10.10.10.1/24"
                "dns": "1.1.1.1",
                "PresharedKey": "True", # String "False" or "True"
                "port": 51820,
                "persistentKeepalive": 0 # Integer
            },
            "clients": {}
        }
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        console.print(f"[bold red]Error:[/bold red] El archivo '{file_path}' no contiene un JSON válido o está dañado.")
        console.print("Se procederá con una estructura base en memoria, pero el archivo original no se modificará hasta un guardado exitoso.")
        return {
            "server": { # Asegurar que server exista con defaults
                "address": IP_SUBNET_PREFIX_DEFAULT, "dns": "1.1.1.1,8.8.8.8", "PresharedKey": "False", "persistentKeepalive": 25, "port": 51820},
            "clients": {}
        }
    except Exception as e:
        console.print(f"[bold red]Ocurrió un error inesperado al cargar '{file_path}':[/bold red] {e}")
        raise # O return {"clients": {}} si prefieres intentar continuar

def save_data(file_path, data):
    """Guarda los datos en el archivo JSON con formato indentado."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]Datos guardados exitosamente en '{file_path}'.[/green]")
        return True # Indicar éxito
    except Exception as e:
        console.print(f"[bold red]Error al guardar los datos en '{file_path}':[/bold red] {e}")
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


def get_next_available_ip(clients_data, prefix, start_octet, max_octet):
    """Obtiene la siguiente dirección IP disponible en la subred especificada."""
    used_octets = set()
    if clients_data:
        for client_uuid, client_details in clients_data.items(): # Iterar también con UUID para mejor logging si es necesario
            client_addresses_field = client_details.get("address")
            
            addresses_to_check = []
            if isinstance(client_addresses_field, str):
                addresses_to_check.append(client_addresses_field) # Tratar la cadena como una lista de un elemento
            elif isinstance(client_addresses_field, list):
                addresses_to_check = client_addresses_field # Usar la lista directamente
            elif client_addresses_field is not None:
                # Si existe pero no es ni cadena ni lista, advertir.
                console.print(f"[yellow]Advertencia:[/yellow] El campo 'address' para el cliente UUID '{client_uuid}' tiene un formato inesperado: {type(client_addresses_field)}. Se omitirá.")

            for addr_cidr in addresses_to_check:
                if isinstance(addr_cidr, str): # Asegurarse de que el elemento sea una cadena antes de hacer split
                    try:
                        ip_part = addr_cidr.split('/')[0] # ej: "10.10.10.2"
                        if ip_part.startswith(prefix):
                            last_octet_str = ip_part.split('.')[-1]
                            if last_octet_str.isdigit():
                                used_octets.add(int(last_octet_str))
                    except (IndexError, ValueError) as e:
                        console.print(f"[yellow]Advertencia:[/yellow] No se pudo parsear la dirección IP: '{addr_cidr}'. Error: {e}")
                else:
                    console.print(f"[yellow]Advertencia:[/yellow] Elemento no válido en la lista de direcciones para el cliente UUID '{client_uuid}': {addr_cidr}. Se omitirá.")
    
    for octet in range(start_octet, max_octet + 1):
        if octet not in used_octets:
            return f"{prefix}{octet}/32" # Devuelve la IP con CIDR /32
            
    return None # No hay IPs disponibles

def add_new_client(client_name):
    """
    Genera un nuevo cliente, lo añade a los datos cargados y guarda el archivo.
    """
    if not client_name or not client_name.strip():
        console.print("[bold red]Error:[/bold red] El nombre del cliente no puede estar vacío.")
        return

    config_data = load_data(WG_CONFIG_FILE)
    
    # Leer configuración del bloque "server"
    server_config = config_data.get("server", {})

    if "clients" not in config_data or not isinstance(config_data["clients"], dict):
        console.print("[bold red]Error:[/bold red] La estructura del archivo de configuración es incorrecta. Falta la sección 'clients' o no es un diccionario.")
        console.print("[yellow]Creando sección 'clients' vacía.[/yellow]")
        config_data["clients"] = {}

    # Determinar el prefijo de IP desde server_config.address
    ip_subnet_prefix = IP_SUBNET_PREFIX_DEFAULT
    server_address_from_config = server_config.get("address")

    if isinstance(server_address_from_config, str) and server_address_from_config.strip():
        addr_strip = server_address_from_config.strip()
        if addr_strip.endswith('.'): # Prioritize if it's already a prefix like "10.10.10."
            ip_parts_check = addr_strip[:-1].split('.') # Remove trailing dot for split
            if len(ip_parts_check) == 3 and all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts_check):
                ip_subnet_prefix = addr_strip
                console.print(f"[info]Usando prefijo de IP del servidor: [cyan]{ip_subnet_prefix}[/cyan]")
            else:
                console.print(f"[yellow]Advertencia:[/yellow] Prefijo 'address' del servidor ('{addr_strip}') no es un formato válido (ej: 192.168.1.). Usando prefijo por defecto: [cyan]{IP_SUBNET_PREFIX_DEFAULT}[/cyan]")
        elif '/' in addr_strip: # Handle if it's an IP/CIDR like "10.10.10.1/24"
            server_ip_part = addr_strip.split('/')[0]
            ip_parts = server_ip_part.split('.')
            if len(ip_parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts):
                ip_subnet_prefix = addr_strip
                console.print(f"[info]Usando prefijo de IP derivado de la dirección del servidor: [cyan]{ip_subnet_prefix}[/cyan]")
            else:
                console.print(f"[yellow]Advertencia:[/yellow] Formato de 'address' del servidor ('{addr_strip}') no es un IPv4 válido para derivar prefijo. Usando prefijo por defecto: [cyan]{IP_SUBNET_PREFIX_DEFAULT}[/cyan]")
        else:
            console.print(f"[yellow]Advertencia:[/yellow] No se pudo determinar el prefijo de IP desde 'address' del servidor ('{addr_strip}'). Usando prefijo por defecto: [cyan]{IP_SUBNET_PREFIX_DEFAULT}[/cyan]")
    else:
        console.print(f"[yellow]Advertencia:[/yellow] 'address' del servidor no encontrada, vacía o en formato inesperado. Usando prefijo por defecto: [cyan]{IP_SUBNET_PREFIX_DEFAULT}[/cyan]")

    # Generar datos para el nuevo cliente
    client_uuid = str(uuid.uuid4())
    private_key, public_key = generate_wg_keys()
    
    next_ip = get_next_available_ip(config_data.get("clients"), ip_subnet_prefix, IP_START_OCTET, IP_MAX_OCTET)
    if not next_ip:
        console.print(f"[bold red]Error:[/bold red] No hay direcciones IP disponibles en la subred {ip_subnet_prefix}{IP_START_OCTET}-{IP_MAX_OCTET}.")
        return

    timestamp = datetime.datetime.utcnow().isoformat(timespec='milliseconds') + "Z"

    # DNS del cliente desde la configuración del servidor
    server_dns_config = server_config.get("dns") # Leer de server.dns
    client_dns_to_set = None
    if isinstance(server_dns_config, str) and server_dns_config.strip():
        client_dns_to_set = server_dns_config.strip()
    elif isinstance(server_dns_config, list): # Handle if DNS is a list
        client_dns_to_set = ",".join(str(d).strip() for d in server_dns_config if str(d).strip())
        if not client_dns_to_set: # If list was empty or all items were empty strings
            client_dns_to_set = None
            
    if client_dns_to_set:
        console.print(f"[info]Usando DNS del servidor para el cliente: [cyan]{client_dns_to_set}[/cyan]")
    else:
        console.print("[yellow]Advertencia:[/yellow] DNS del servidor no configurado o vacío. El cliente no tendrá DNS preconfigurado.")

    # PresharedKey
    preshared_key_to_set = None
    # Leer de server.PresharedKey (string "True" or "False")
    generate_psk_str = server_config.get("PresharedKey", "False") 
    if str(generate_psk_str).lower() == "true":
        console.print("[info]Generando PresharedKey para el cliente según la configuración del servidor...[/info]")
        preshared_key_to_set = generate_preshared_key()

    # PersistentKeepalive
    persistent_keepalive_default = 0 # Default if not in server_config or invalid
    persistent_keepalive_to_set = server_config.get("persistentKeepalive", persistent_keepalive_default)
    if not isinstance(persistent_keepalive_to_set, int) or persistent_keepalive_to_set < 0:
        console.print(f"[yellow]Advertencia:[/yellow] 'persistentKeepalive' en la configuración del servidor ('{persistent_keepalive_to_set}') no es un entero no negativo. Usando por defecto: {persistent_keepalive_default}.")
        persistent_keepalive_to_set = persistent_keepalive_default
    elif persistent_keepalive_to_set > 0: # Only print if it's a positive value being used
         console.print(f"[info]Usando PersistentKeepalive del servidor para el cliente: [cyan]{persistent_keepalive_to_set}[/cyan]")
    
    new_client_data = {
        "id": client_uuid,
        "name": client_name.strip(),
        "address": next_ip, # Guardar como cadena de texto
        "privateKey": private_key,
        "publicKey": public_key,
        "PresharedKey": preshared_key_to_set,
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "dns": client_dns_to_set, 
        "persistentKeepalive": persistent_keepalive_to_set, # Guardar como entero
        "allowedIPs": "0.0.0.0/0, ::/0", # Guardar como cadena de texto
        "enabled": True
    }

    # Añadir el nuevo cliente
    config_data["clients"][client_uuid] = new_client_data
    console.print(f"\n[bold]Cliente '{client_name}' preparado para ser añadido:[/bold]")
    console.print(f"  UUID: [cyan]{client_uuid}[/cyan]")
    console.print(f"  IP: [cyan]{next_ip}[/cyan]")

    # Guardar los datos actualizados
    if save_data(WG_CONFIG_FILE, config_data): # save_data now returns True on success, False on failure
        console.print("\n[bold green]Cliente añadido y guardado. Detalles:[/bold green]")
        details_table = Table(show_header=True, header_style="bold magenta", box=HEAVY_HEAD) # Sin título y con box HEAVY_HEAD
        details_table.add_column("Campo", style="cyan", no_wrap=True, min_width=25)
        details_table.add_column("Valor", style="white", min_width=40)

        for key, value in new_client_data.items():
            # Formatear el valor: si es None, mostrar "No establecido", sino convertir a cadena.
            # Usar Text para permitir estilos como italic dim.
            display_value = str(value) if value is not None else Text("No establecido", style="italic dim")
            
            # Formatear el nombre del campo (ej: privateKey -> Privatekey)
            # Este formato es consistente con wg_manager_cli.py
            formatted_key_display = key.replace('_', ' ').capitalize()
            details_table.add_row(formatted_key_display, display_value)
        
        console.print(details_table)
    else:
        console.print("[bold red]Error al guardar los datos del cliente. No se mostrarán los detalles en tabla.[/bold red]")

if __name__ == "__main__":
    # Ejemplo de uso:
    console.rule("[bold blue]Añadir Nuevo Cliente WireGuard[/bold blue]")
    client_name_input = console.input("[b]Introduce el nombre para el nuevo cliente:[/b] ")
    if client_name_input:
        add_new_client(client_name_input)
    else:
        console.print("[yellow]No se introdujo un nombre. No se añadió ningún cliente.[/yellow]")