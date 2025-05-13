import os
import sys
import json

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text
except ImportError:
    print("La biblioteca 'rich' no está instalada. Por favor, instálala con: pip install rich")
    sys.exit(1)

console = Console()

# Definición de WG_CONFIG_FILE (debe ser consistente con tus otros scripts)
WG_CONFIG_FILE = "wg0.json"
DEFAULT_SERVER_CONFIG_FILENAME = "wg_server.conf"

def load_config_data():
    """Carga los datos completos desde el archivo JSON de configuración."""
    if not os.path.exists(WG_CONFIG_FILE):
        console.print(f"[bold red]Error:[/bold red] El archivo de configuración '{WG_CONFIG_FILE}' no existe.")
        return None
    try:
        with open(WG_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        console.print(f"[bold red]Error:[/bold red] El archivo '{WG_CONFIG_FILE}' no contiene un JSON válido.")
        return None
    except Exception as e:
        console.print(f"[bold red]Error inesperado al cargar '{WG_CONFIG_FILE}':[/bold red] {e}")
        return None

def save_text_to_file(filepath, content):
    """Guarda el contenido de texto en un archivo."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        console.print(f"[green]Configuración guardada exitosamente en '{filepath}'.[/green]")
        return True
    except Exception as e:
        console.print(f"[bold red]Error al guardar el archivo '{filepath}':[/bold red] {e}")
        return False

def generate_wg_config_string(server_config, clients_data, server_interface_name="wg0"):
    """Genera la cadena de configuración de WireGuard para el servidor."""
    config_lines = []

    # --- [Interface] section for the server ---
    config_lines.append("[Interface]")
    
    server_private_key = server_config.get("privateKey")
    if not server_private_key:
        console.print(f"[bold red]Error Crítico:[/bold red] 'privateKey' del servidor no encontrado en '{WG_CONFIG_FILE}' bajo la sección 'server'.")
        console.print("Este campo es esencial para la sección [Interface] del servidor.")
        console.print(f"Por favor, añade 'privateKey': 'SU_CLAVE_PRIVADA_DE_SERVIDOR' a la sección 'server' en '{WG_CONFIG_FILE}'.")
        return None
    config_lines.append(f"PrivateKey = {server_private_key}")

    # Determinar la IP y subred de la interfaz del servidor
    server_address_config = server_config.get("address")
    if server_address_config:
        config_lines.append(f"Address = {server_address_config}")
    else:
        console.print(f"[bold red]Error Crítico:[/bold red] No se encontró 'address' en la configuración del servidor en '{WG_CONFIG_FILE}'.")
        config_lines.append("# Address = <SERVER_WG_IP/SUBNET_EJ_10.10.10.1/24>  <-- ¡¡CRÍTICO!! Por favor, establece esto manualmente.")

    listen_port = server_config.get("port", 51820)
    config_lines.append(f"ListenPort = {listen_port}")

    # Reglas PostUp/PostDown (ejemplos, el usuario debe adaptarlas)
    public_interface_placeholder = "<YOUR_PUBLIC_INTERFACE_eg_eth0>" # Placeholder
    config_lines.append(f"PostUp =  iptables -t nat -A POSTROUTING -s {server_address_config.split('/')[0]}/24 -o {public_interface_placeholder} -j MASQUERADE; iptables -A INPUT -p udp -m udp --dport {listen_port} -j ACCEPT; iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT;")
    config_lines.append(f"PostDown =  iptables -t nat -D POSTROUTING -s {server_address_config.split('/')[0]}/24 -o {public_interface_placeholder} -j MASQUERADE; iptables -D INPUT -p udp -m udp --dport {listen_port} -j ACCEPT; iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT;")
    """
    config_lines.append(f"# PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {public_interface_placeholder} -j MASQUERADE")
    config_lines.append(f"# PostUp = ip6tables -A FORWARD -i %i -j ACCEPT; ip6tables -t nat -A POSTROUTING -o {public_interface_placeholder} -j MASQUERADE")
    config_lines.append(f"# PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {public_interface_placeholder} -j MASQUERADE")
    config_lines.append(f"# PostDown = ip6tables -D FORWARD -i %i -j ACCEPT; ip6tables -t nat -D POSTROUTING -o {public_interface_placeholder} -j MASQUERADE")
    config_lines.append("SaveConfig = false # O true si deseas que wg-quick guarde cambios en este archivo")
    config_lines.append("")
    """
    # --- [Peer] sections for enabled clients ---
    if not clients_data:
        console.print("[yellow]Advertencia: No hay datos de clientes en el archivo de configuración.[/yellow]")
    
    enabled_clients_count = 0
    for client_uuid, client_details in clients_data.items():
        if client_details.get("enabled", False): # Solo añadir clientes habilitados
            # Esta condición asegura que solo los clientes con "enabled": true en wg0.json sean procesados.
            # Si "enabled" es false, o si la clave "enabled" falta para un cliente
            # (.get() devolverá False como valor por defecto), la sección [Peer] de ese cliente se omitirá.
            # Esto asume que "enabled" se almacena como un valor booleano en wg0.json,
            # lo cual es consistente con cómo add_client.py y edit_clients.py lo manejan.
            enabled_clients_count += 1
            config_lines.append("[Peer]")
            config_lines.append(f"# Client Name: {client_details.get('name', 'N/A')}")
            config_lines.append(f"# Client UUID: {client_uuid}")
            
            public_key = client_details.get("publicKey")
            if public_key:
                config_lines.append(f"PublicKey = {public_key}")
            else:
                config_lines.append("# PublicKey = <CLAVE_PUBLICA_DEL_CLIENTE_FALTA>")
                console.print(f"[yellow]Advertencia:[/yellow] Cliente '{client_details.get('name', client_uuid)}' no tiene 'publicKey'.")

            preshared_key = client_details.get("presharedKey")
            if preshared_key: # Se añade la PresharedKey solo si existe y tiene un valor.
                              # Si client_details.get("presharedKey") devuelve None (ej. null en JSON) o una cadena vacía,
                              # la línea PresharedKey no se incluirá para este peer.
                config_lines.append(f"PresharedKey = {preshared_key}")

            # AllowedIPs para la configuración del servidor es la IP WireGuard del cliente
            client_wg_address = client_details.get("address") # Debería ser como "10.10.10.2/32"
            
            # El campo 'address' puede ser una cadena o una lista (aunque add_client.py lo guarda como cadena)
            allowed_ip_to_use = None
            if isinstance(client_wg_address, str):
                allowed_ip_to_use = client_wg_address
            elif isinstance(client_wg_address, list):
                if client_wg_address: # Tomar el primero si es una lista
                    allowed_ip_to_use = client_wg_address[0] 
                else:
                    console.print(f"[yellow]Advertencia:[/yellow] Cliente '{client_details.get('name', client_uuid)}' tiene una lista de 'address' vacía.")
            
            if allowed_ip_to_use:
                config_lines.append(f"AllowedIPs = {allowed_ip_to_use}")
            else:
                config_lines.append("# AllowedIPs = <IP_WIREGUARD_DEL_CLIENTE_FALTA>")
                console.print(f"[yellow]Advertencia:[/yellow] Cliente '{client_details.get('name', client_uuid)}' no tiene 'address' para AllowedIPs.")

            # PersistentKeepalive (opcional en la sección Peer del servidor, más común en el cliente)
            # client_persistent_keepalive = client_details.get("persistentKeepalive")
            # if isinstance(client_persistent_keepalive, int) and client_persistent_keepalive > 0:
            #     config_lines.append(f"PersistentKeepalive = {client_persistent_keepalive}")
            config_lines.append("") # Nueva línea después de cada [Peer]
    
    if enabled_clients_count == 0:
        console.print("[yellow]Advertencia: No se encontraron clientes habilitados ('enabled: true') para añadir a la configuración.[/yellow]")
        if not clients_data: # Si no había clientes en absoluto
             pass # Ya se advirtió antes
        else: # Si había clientes pero ninguno habilitado
             console.print("[info]Asegúrate de que los clientes que deseas incluir tengan 'enabled: true' en el archivo JSON.[/info]")


    return "\n".join(config_lines)

def main_generate_config():
    """Función principal para generar el archivo de configuración del servidor WireGuard."""
    console.clear()
    console.print(Panel(
        Text("Generador de Configuración WireGuard (Servidor)", style="bold white on blue", justify="center"),
        title="[bold blue]Generar Configuración WG[/bold blue]",
        border_style="blue",
        padding=(1, 2)
    ))

    output_filename_input = Prompt.ask(
        "Introduce el nombre para el archivo de configuración del servidor",
        default=DEFAULT_SERVER_CONFIG_FILENAME
    ).strip()

    if not output_filename_input:
        console.print("[yellow]Nombre de archivo vacío. Operación cancelada.[/yellow]")
        return

    # Asegurar que el nombre del archivo final tenga la extensión .conf
    final_output_filename = output_filename_input
    if not output_filename_input.lower().endswith(".conf"):
        final_output_filename = output_filename_input + ".conf"


    config_data = load_config_data()
    if not config_data:
        console.print(f"[red]No se pudo cargar la configuración desde '{WG_CONFIG_FILE}'. No se puede continuar.[/red]")
        return

    server_conf = config_data.get("server")
    clients_conf = config_data.get("clients") # Puede ser None si la clave no existe

    if not server_conf:
        console.print(f"[bold red]Error:[/bold red] La sección 'server' no se encuentra en '{WG_CONFIG_FILE}'.")
        return
    if clients_conf is None: 
        console.print(f"[yellow]Advertencia:[/yellow] La sección 'clients' no se encuentra en '{WG_CONFIG_FILE}' o es nula. No se añadirán peers.")
        clients_conf = {} # Tratar como vacío si no existe para evitar errores

    console.print("\n[cyan]Generando configuración del servidor WireGuard...[/cyan]")
    wg_config_content = generate_wg_config_string(server_conf, clients_conf)

    if wg_config_content:
        if save_text_to_file(final_output_filename, wg_config_content):
            console.print(f"\n[info]Recuerda revisar y personalizar las reglas 'PostUp' y 'PostDown' en '{final_output_filename}' según la interfaz de red pública de tu servidor.[/info]")
            if "privateKey" not in server_conf or not server_conf["privateKey"]:
                 console.print(f"[bold yellow]¡IMPORTANTE![/bold yellow] La 'privateKey' del servidor no estaba definida en '{WG_CONFIG_FILE}'. La configuración generada es incompleta y no funcionará sin ella.")
            if not server_conf.get("address"):
                 console.print(f"[bold yellow]¡IMPORTANTE![/bold yellow] El 'address' del servidor no estaba bien definido en '{WG_CONFIG_FILE}'. La IP de la interfaz en la configuración generada necesita ser establecida manualmente.")

        else:
            console.print("[red]La configuración se generó pero no pudo ser guardada.[/red]")
    else:
        console.print("[red]No se pudo generar el contenido de la configuración del servidor WireGuard debido a errores previos (revisa los mensajes).[/red]")

    console.rule()
    Prompt.ask("[dim]Presiona Enter para continuar...[/dim]", default="", show_default=False)


if __name__ == "__main__":
    main_generate_config()
