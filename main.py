import os
import sys
import json 
import subprocess # Necesario para llamar a wg_conf.py
import qrcode
import psutil
import ipaddress
import signal

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
except ImportError:
    print("La biblioteca 'rich' no está instalada. Por favor, instálala con: pip install rich")
    sys.exit(1)

try:
    from list_clients import load_data as list_load_data # load_data de list_clients devuelve lista de clientes
    from add_client import add_new_client as add_client_add_new_client
    from add_client import generate_wg_keys
    from add_client import WG_CONFIG_FILE
    from add_client import load_data
    from edit_clients import edit_client_interactive # Nueva importación
    from edit_server import view_server_config
except ImportError as e:
    if 'Console' in globals():
        console = Console()
        console.print(f"[bold red]Error al importar módulos necesarios:[/bold red] {e}")
        console.print("Asegúrate de que los archivos 'list_clients.py', 'add_client.py' y 'edit_clients.py' estén en el mismo directorio o sean accesibles.")
    else:
        print(f"Error al importar módulos necesarios: {e}")
        print("Asegúrate de que los archivos 'list_clients.py', 'add_client.py' y 'edit_clients.py' estén en el mismo directorio o sean accesibles.")
    sys.exit(1)

console = Console()

# Manejar la señal de interrupción (Ctrl+C)
def handle_exit_signal(signum, frame):
    console.print("\n[bold yellow]Saliendo del programa...[/bold yellow]")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit_signal)

def get_display_ip(address_field):
    if not address_field:
        return "[italic dim]N/A[/italic dim]"
    ip_to_display = ""
    if isinstance(address_field, list):
        if address_field:
            ip_to_display = address_field[0]
        else:
            return "[italic dim]N/A (lista vacía)[/italic dim]"
    elif isinstance(address_field, str):
        ip_to_display = address_field
    else:
        return "[italic dim]Formato desconocido[/italic dim]"
    return ip_to_display.split('/')[0]



def display_clients(server_id):
    """Muestra una tabla resumen de clientes y permite ver/editar detalles."""
    clientes = []  # Inicializar lista de clientes
    while True:  # Bucle para permitir refrescar la lista después de editar
        console.clear()
        console.print(Panel("[bold cyan]Listado de Clientes (Resumen)[/bold cyan]", expand=False, border_style="cyan"))
        clientes = list_load_data(server_id)  # Cargar/Recargar clientes
        if not clientes:
            console.clear()
            console.print("[yellow]No se encontraron datos de clientes para mostrar o se produjo un error durante la carga.[/yellow]")
            console.print(f"Archivo de configuración verificado: [yellow]{WG_CONFIG_FILE}[/yellow]")
            Prompt.ask("[dim]Presiona Enter para volver al menú principal...[/dim]", default="", show_default=False)
            return  # Salir de display_clients si no hay clientes

        summary_table = Table(title="[bold]Clientes Registrados[/bold]", show_header=True, header_style="bold magenta")
        summary_table.add_column("#", style="dim", width=4, justify="right")
        summary_table.add_column("Nombre", style="green", min_width=20)
        summary_table.add_column("Dirección IP", style="yellow", min_width=15)

        for i, cliente_data in enumerate(clientes):
            num = str(i + 1)
            name = cliente_data.get('name', '[italic dim]Sin Nombre[/italic dim]')
            ip_address = get_display_ip(cliente_data.get('address'))
            summary_table.add_row(num, name, ip_address)
        
        console.print(summary_table)
        console.print(Panel(f"Total de clientes: [bold]{len(clientes)}[/bold]. Archivo: [yellow]{WG_CONFIG_FILE}[/yellow]", expand=False, border_style="yellow"))
        console.rule()


        try:
            client_num_str = Prompt.ask(
                f"Introduce el número del cliente para ver/editar detalles (1-{len(clientes)}) o Enter para volver."
            )
            if not client_num_str.strip():
                return

            client_num = int(client_num_str)
            
            if 1 <= client_num <= len(clientes):
                selected_client_data = clientes[client_num - 1]
                client_uuid_for_edit = selected_client_data.get('uuid')

                if not client_uuid_for_edit:
                    console.clear()
                    needs_refresh = True
                    console.print("[red]Error: No se pudo determinar el UUID del cliente para la edición.[/red]")
                    Prompt.ask("[dim]No es posible editar este cliente.[/dim]")
                    continue
                
                edited = display_single_client_details_and_edit_option(selected_client_data, client_num, client_uuid_for_edit)
                if edited:
                    needs_refresh = True # Marcar para recargar la lista de clientes
            else:
                console.clear()
                needs_refresh = True
                Prompt.ask(f"[yellow]Número de cliente inválido. Debe estar entre 1 y {len(clientes)}.[/yellow]")

        except ValueError:
            console.clear()
            needs_refresh = True
            Prompt.ask("[red]Entrada inválida. Por favor, introduce un número.[/red]")
        except Exception as e:
            console.clear()
            needs_refresh = True
            Prompt.ask(f"[bold red]Ocurrió un error inesperado:[/bold red] {e}")

def display_single_client_details_and_edit_option(client_data, client_number, client_uuid):
    """Muestra detalles y ofrece opciones para editar, mostrar QR o generar archivo .conf."""
    while True:
        console.clear()
        client_name = client_data.get('name', f'Cliente #{client_number}')
        console.print(Panel(f"[bold magenta]Detalles Completos del Cliente: {client_name} (ID: {client_uuid})[/bold magenta]",
                          expand=False, border_style="magenta"))

        details_table = Table(show_header=True, header_style="bold cyan", border_style="green")
        details_table.add_column("Detalle", style="dim cyan", width=25)
        details_table.add_column("Valor", style="white")

        for campo, valor in client_data.items():
            nombre_campo_formateado = str(campo).replace('_', ' ').capitalize()
            if isinstance(valor, (list, dict)):
                valor_str = json.dumps(valor, indent=2)
            elif valor is None:
                valor_str = "[italic dim]N/A[/italic dim]"
            else:
                valor_str = str(valor)
            details_table.add_row(nombre_campo_formateado, valor_str)
        
        console.print(details_table)
        console.rule()

        console.print("[bold cyan]Opciones disponibles:[/bold cyan]")
        console.print("1. [green]Editar cliente[/green]")
        console.print("2. [yellow]Mostrar QR en consola[/yellow]")
        console.print("3. [blue]Generar archivo .conf[/blue]")
        console.print("4. [red]Volver al listado[/red]")

        option = Prompt.ask("Selecciona una opción", choices=["1", "2", "3", "4"], default="4").strip().lower()

        if option == "1":
            console.clear()
            changes_made = edit_client_interactive(client_uuid) # Pasar el UUID
            if changes_made:
                console.clear()
                console.print("[green]Los datos del cliente han sido actualizados.[/green]")
                Prompt.ask("[dim]Presiona Enter para continuar...[/dim]", default="", show_default=False)
                return True # Indicar que hubo cambios y se guardaron
            else:
                console.clear()
                console.print("[yellow]No se realizaron cambios en el cliente.[/yellow]")
                Prompt.ask("[dim]Presiona Enter para continuar...[/dim]", default="", show_default=False)
        elif option == "2":
            console.clear()
            # Generar configuración para QR
            server_config = load_data(WG_CONFIG_FILE).get("server", {})
            qr_config = (
                f"[Interface]\n"
                f"PrivateKey = {client_data.get('privateKey')}\n"
                f"Address = {client_data.get('address')}\n"
                f"DNS = {server_config.get('dns')}\n\n"
                f"[Peer]\n"
                f"PublicKey = {server_config.get('publicKey')}\n"
                f"Endpoint = {server_config.get('endpoint')}:{server_config.get('port')}\n"
                f"AllowedIPs = 0.0.0.0/0, ::/0\n"
            )

            preshared_key = client_data.get('PresharedKey')
            if preshared_key:
                qr_config += f"PresharedKey = {preshared_key}\n"

            # Mostrar QR en consola con un marco blanco
            qr = qrcode.QRCode(border=4)  # Ajustar el tamaño del borde
            qr.add_data(qr_config)
            qr.make(fit=True)
            qr.print_ascii(invert=True)  # Invertir colores para mejor contraste
            console.print(f"[green]Mostrando QR de[/green] [yelow]{client_data.get("name")}[/yelow][green].[/green]")
            Prompt.ask("[dim]Presiona Enter para continuar...[/dim]", default="", show_default=False)
        elif option == "3":
            console.clear()
            # Generar archivo de configuración
            server_config = load_data(WG_CONFIG_FILE).get("server", {})
            qr_config = (
                f"[Interface]\n"
                f"PrivateKey = {client_data.get('PrivateKey')}\n"
                f"Address = {client_data.get('address')}\n"
                f"DNS = {server_config.get('dns')}\n\n"
                f"[Peer]\n"
                f"PublicKey = {server_config.get('publicKey')}\n"
                f"Endpoint = {server_config.get('endpoint')}:{server_config.get('port')}\n"
                f"AllowedIPs = 0.0.0.0/0, ::/0\n"
            )

            preshared_key = client_data.get('PresharedKey')
            if preshared_key:
                qr_config += f"PresharedKey = {preshared_key}\n"

            config_file_path = f"{client_name}.conf"
            with open(config_file_path, "w") as config_file:
                config_file.write(qr_config)
            console.print(f"[green]Archivo de configuración generado y guardado en: {config_file_path}[/green]")
            Prompt.ask("[dim]Presiona Enter para continuar...[/dim]", default="", show_default=False)
        elif option == "4":
            return True # Volver al listado

        console.rule()

def prompt_add_new_client():
    console.clear()
    console.print(Panel("[bold green]Añadir Nuevo Cliente[/bold green]", expand=False, border_style="green"))
    client_name_input = Prompt.ask("Introduce el nombre para el nuevo cliente (o deja en blanco para cancelar)")
    
    if client_name_input and client_name_input.strip():
        console.clear()
        add_client_add_new_client(client_name_input) 
    elif not client_name_input.strip():
        console.clear()
        console.print("[yellow]Operación cancelada. No se añadió ningún cliente.[/yellow]")
        Prompt.ask("[dim]Presiona Enter para continuar...[/dim]", default="", show_default=False)
    else: 
        console.clear()
        console.print("[red]Nombre de cliente inválido. No se añadió ningún cliente.[/red]")
        Prompt.ask("[dim]Presiona Enter para continuar...[/dim]", default="", show_default=False)
    console.rule(style="dim green")

def generate_keys():
    """Genera una clave privada y su correspondiente clave pública."""
    try:
        private_key = subprocess.check_output(['wg', 'genkey']).decode('utf-8').strip()
        public_key = subprocess.check_output(['wg', 'pubkey'], input=private_key.encode('utf-8')).decode('utf-8').strip()
        return private_key, public_key
    except FileNotFoundError:
        console.print("[bold yellow]Advertencia:[/bold yellow] Comando 'wg' no encontrado. Usando placeholders para las claves.")
        console.print("Por favor, asegúrate de que las herramientas de WireGuard estén instaladas y en el PATH para generar claves reales.")
        return "PLACEHOLDER_PRIVATE_KEY_wg_not_found", "PLACEHOLDER_PUBLIC_KEY_wg_not_found"
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error ejecutando el comando 'wg':[/bold red] {e}")
        console.print("[yellow]Usando placeholders para las claves.[/yellow]")
        return "PLACEHOLDER_PRIVATE_KEY_wg_error", "PLACEHOLDER_PUBLIC_KEY_wg_error"

def list_network_interfaces():
    """Lista las interfaces de red disponibles en el sistema."""
    interfaces = psutil.net_if_addrs().keys()
    return list(interfaces)

def create_wg0_json():
    """Crea el archivo wg0.json con los datos proporcionados por el usuario."""
    console.print("[bold green]Creando archivo wg0.json...[/bold green]")

    # Solicitar datos al usuario
    while True:
        address = Prompt.ask("Introduce la dirección IP completa con máscara:", default= "10.0.10.1/24")
        try:
            ipaddress.ip_network(address, strict=False)  # Validar formato CIDR
            break
        except ValueError:
            console.print("[bold red]Error:[/bold red] Dirección IP inválida. Intenta de nuevo.")

    dns = Prompt.ask("Introduce el servidor DNS", default="1.1.1.1")
    port = Prompt.ask("Introduce el puerto", default="51820")
    pre_shared_key = Confirm.ask("¿Deseas habilitar PresharedKey?", default=True)
    endpoint = Prompt.ask("Introduce el endpoint", default="0.0.0.0")
    persistent_keepalive = Prompt.ask("Introduce el valor de persistentKeepalive:", default="0")

    # Listar interfaces de red y solicitar selección
    interfaces = list_network_interfaces()
    if not interfaces:
        console.print("[bold red]Error:[/bold red] No se encontraron interfaces de red disponibles.")
        return

    console.print("[bold cyan]Interfaces de red disponibles:[/bold cyan]")
    for i, iface in enumerate(interfaces, start=1):
        console.print(f"{i}. {iface}")

    selected_interface_index = Prompt.ask(
        "Selecciona el número de la interfaz de red a usar",
        choices=[str(i) for i in range(1, len(interfaces) + 1)]
    )
    selected_interface = interfaces[int(selected_interface_index) - 1]

    # Generar claves
    private_key, public_key = generate_keys()

    # Crear el contenido del archivo wg0.json
    wg0_data = {
        "server": {
            "privateKey": private_key,
            "publicKey": public_key,
            "address": address,
            "dns": dns,
            "port": int(port),
            "PresharedKey": str(pre_shared_key),
            "endpoint": endpoint,
            "persistentKeepalive": int(persistent_keepalive),
            "interface": selected_interface
        },
        "clients": {}
    }

    # Guardar en wg0.json
    with open("wg0.json", "w") as wg0_file:
        json.dump(wg0_data, wg0_file, indent=4)

    console.print("[green]Archivo wg0.json creado exitosamente.[/green]")

# Verificar si el archivo wg0.json existe
if not os.path.exists("wg0.json"):
    create_wg0_json()

def cargar_configuracion():
    if not os.path.exists(WG_CONFIG_FILE):
        return {"servers": {}}
    with open(WG_CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def seleccionar_servidor():
    config = cargar_configuracion()
    servers = config.get("servers", {})
    if not servers:
        console.print("[yellow]No hay servidores configurados. Debes agregar uno primero.[/yellow]")
        return None, config
    server_ids = list(servers.keys())
    console.print("[bold cyan]Servidores disponibles:[/bold cyan]")
    for idx, sid in enumerate(server_ids, 1):
        nombre = servers[sid].get('name', sid)
        console.print(f"{idx}. [green]{nombre}[/green] (ID: {sid})")
    idx_str = Prompt.ask(f"Selecciona el número del servidor (1-{len(server_ids)})", default="1")
    try:
        idx = int(idx_str)
        if 1 <= idx <= len(server_ids):
            return server_ids[idx-1], config
    except Exception:
        pass
    console.print("[red]Selección inválida.[/red]")
    return None, config

def agregar_servidor():
    config = cargar_configuracion()
    servers = config.setdefault("servers", {})
    server_id_name = Prompt.ask("Introduce un nombre único para el nuevo servidor")
    if not server_id_name or server_id_name in servers:
        Prompt.ask("[red]ID inválido o ya existente.[/red]")
        return
    private_key, public_key = generate_keys()
    address = Prompt.ask("Dirección IP/máscara del servidor", default="10.10.10.1/24")
    dns = Prompt.ask("DNS del servidor", default="1.1.1.1")
    port = Prompt.ask("Puerto", default="51820")
    endpoint = Prompt.ask("Endpoint", default="0.0.0.0")
    persistent_keepalive = Prompt.ask("PersistentKeepalive", default="0")
    servers[server_id_name] = {
        "publicKey": public_key,
        "privateKey": private_key,
        "name": server_id_name,
        "address": address,
        "dns": dns,
        "port": int(port),
        "endpoint": endpoint,
        "persistentKeepalive": int(persistent_keepalive),
        "clients": {}
    }
    with open(WG_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    console.print(f"[green]Servidor '{server_id_name}' añadido correctamente.[/green]")
    Prompt.ask("Presiona Enter para continuar...")

def eliminar_servidor():
    server_id, config = seleccionar_servidor()
    if not server_id:
        return
    nombre = config['servers'][server_id].get('name', server_id)
    if Confirm.ask(f"¿Seguro que deseas eliminar el servidor '{nombre}' (ID: {server_id})? Esta acción es irreversible.", default=False):
        del config['servers'][server_id]
        with open(WG_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        console.print(f"[red]Servidor '{nombre}' eliminado.[/red]")
        Prompt.ask("Presiona Enter para continuar...")

def main_menu():
    while True:
        console.clear()
        console.print(Panel(
            Text("Gestor de WireGuard Multi-Servidor (CLI)", style="bold white on cyan", justify="center"),
            title="[bold blue]Menú Principal[/bold blue]",
            border_style="blue",
            padding=(1, 2)
        ))
        console.print("1. [bold cyan]Listar/Editar clientes de un servidor[/bold cyan]")
        console.print("2. [bold cyan]Añadir un nuevo cliente a un servidor[/bold cyan]")
        console.print("3. [bold cyan]Agregar un nuevo servidor[/bold cyan]")
        console.print("4. [bold cyan]Editar configuración de un servidor[/bold cyan]")
        console.print("5. [bold cyan]Eliminar un servidor[/bold cyan]")
        console.print("6. [bold red]Salir[/bold red]")
        console.rule(style="dim blue")
        opcion = Prompt.ask("Selecciona una opción", choices=["1","2","3","4","5","6"], default="6")
        if opcion == "1":
            server_id, _ = seleccionar_servidor()
            if server_id:
                display_clients(server_id)
        elif opcion == "2":
            server_id, _ = seleccionar_servidor()
            if server_id:
                nombre_cliente = Prompt.ask("Nombre del nuevo cliente")
                if nombre_cliente:
                    add_client_add_new_client(nombre_cliente, server_id)
        elif opcion == "3":
            agregar_servidor()
        elif opcion == "4":
            server_id, _ = seleccionar_servidor()
            if server_id:
                # Llama a la función de edición de servidor
                pass
        elif opcion == "5":
            eliminar_servidor()
        elif opcion == "6":
            console.print("[yellow]Saliendo...[/yellow]")
            break

if __name__ == "__main__":
    if not os.path.exists(WG_CONFIG_FILE):
        agregar_servidor()
    main_menu()
