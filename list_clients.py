import uuid
import json 
import os
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

WG_CONFIG_FILE = "wg_data.json"
console = Console()

def load_data(server_id=None):
    """Carga los datos de los clientes de un servidor específico desde wg_data.json."""
    if not os.path.exists(WG_CONFIG_FILE):
        console.print(f"[yellow]Advertencia: El archivo '{WG_CONFIG_FILE}' no existe. No se pueden cargar clientes.[/yellow]")
        return []
    try:
        with open(WG_CONFIG_FILE, 'r', encoding='utf-8') as f:
            data_from_file = json.load(f)
        servers = data_from_file.get("servers", {})
        if not servers:
            console.print(f"[yellow]No hay servidores definidos en '{WG_CONFIG_FILE}'.[/yellow]")
            return []
        if server_id is None:
            # Si no se especifica, pedir al usuario seleccionar
            server_id = select_server_interactive(servers)
            if not server_id:
                return []
        server = servers.get(server_id)
        if not server:
            console.print(f"[red]Servidor '{server_id}' no encontrado.[/red]")
            return []
        clients_dict = server.get("clients", {})
        if not isinstance(clients_dict, dict):
            console.print(f"[red]La sección 'clients' del servidor '{server_id}' no es un diccionario.[/red]")
            return []
        processed_clients = []
        for client_uuid, client_info in clients_dict.items():
            if isinstance(client_info, dict):
                current_client_data = {'uuid': client_uuid}
                current_client_data.update(client_info)
                processed_clients.append(current_client_data)
        return processed_clients
    except json.JSONDecodeError:
        console.print(f"[red]El archivo '{WG_CONFIG_FILE}' no contiene un JSON válido o está vacío.[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Ocurrió un error inesperado al leer o procesar el archivo '{WG_CONFIG_FILE}': {e}[/red]")
        return []

def select_server_interactive(servers_dict):
    """Permite al usuario seleccionar un servidor de la lista."""
    if not servers_dict:
        console.print("[yellow]No hay servidores disponibles.[/yellow]")
        return None
    server_ids = list(servers_dict.keys())
    if len(server_ids) == 1:
        return server_ids[0]
    console.print(Panel("[bold cyan]Selecciona un servidor:[/bold cyan]", border_style="cyan"))
    for idx, sid in enumerate(server_ids, 1):
        name = servers_dict[sid].get("name", sid)
        console.print(f"{idx}. [green]{name}[/green] (ID: {sid})")
    while True:
        choice = Prompt.ask(f"Introduce el número del servidor (1-{len(server_ids)}) o Enter para cancelar")
        if not choice.strip():
            return None
        try:
            idx = int(choice)
            if 1 <= idx <= len(server_ids):
                return server_ids[idx-1]
            else:
                console.print("[yellow]Número fuera de rango.[/yellow]")
        except ValueError:
            console.print("[red]Entrada inválida.[/red]")

if __name__ == "__main__":
    # Cargar todos los servidores
    if not os.path.exists(WG_CONFIG_FILE):
        console.print(f"[red]El archivo '{WG_CONFIG_FILE}' no existe.[/red]")
        exit(1)
    with open(WG_CONFIG_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    servers = data.get("servers", {})
    server_id = select_server_interactive(servers)
    if not server_id:
        console.print("[yellow]Operación cancelada.[/yellow]")
        exit(0)
    clientes = load_data(server_id)
    if clientes:
        print("\nListado de Clientes y sus campos:")
        print("------------------------------------")
        for i, cliente_data in enumerate(clientes):
            print(f"\nCliente #{i + 1}:")
            for campo, valor in cliente_data.items():
                nombre_campo_formateado = str(campo).replace('_', ' ').capitalize()
                print(f"  {nombre_campo_formateado}: {valor}")
            if i < len(clientes) - 1:
                print("---")
        print("------------------------------------")
    else:
        print("No se encontraron datos de clientes para mostrar o se produjo un error durante la carga.")
