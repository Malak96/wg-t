import os
import sys
import json 
import subprocess # Necesario para llamar a gw_conf.py

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
    from add_client import WG_CONFIG_FILE
    from edit_clients import edit_client_interactive # Nueva importación
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



def display_clients():
    """Muestra una tabla resumen de clientes y permite ver/editar detalles."""
    needs_refresh = True
    clientes = [] # Inicializar lista de clientes

    while True: # Bucle para permitir refrescar la lista después de editar
        if needs_refresh:
            console.clear()
            console.print(Panel("[bold cyan]Listado de Clientes (Resumen)[/bold cyan]", expand=False, border_style="cyan"))
            clientes = list_load_data() # Cargar/Recargar clientes
            if not clientes:
                console.print("[yellow]No se encontraron datos de clientes para mostrar o se produjo un error durante la carga.[/yellow]")
                console.print(f"Archivo de configuración verificado: [yellow]{WG_CONFIG_FILE}[/yellow]")
                return # Salir de display_clients si no hay clientes

            summary_table = Table(title="[bold]Clientes Registrados[/bold]", show_header=True, header_style="bold magenta")
            summary_table.add_column("#", style="dim", width=4, justify="right")
            summary_table.add_column("Nombre", style="green", min_width=20)
            summary_table.add_column("UUID (ID)", style="cyan", min_width=36) # El UUID que es la clave en el JSON
            summary_table.add_column("Dirección IP", style="yellow", min_width=15)

            for i, cliente_data in enumerate(clientes):
                num = str(i + 1)
                name = cliente_data.get('name', '[italic dim]Sin Nombre[/italic dim]')
                # list_clients.load_data() añade la clave del JSON como 'uuid' en cada diccionario de cliente.
                uuid_display = cliente_data.get('uuid', '[italic dim]N/A[/italic dim]')
                ip_address = get_display_ip(cliente_data.get('address'))
                summary_table.add_row(num, name, uuid_display, ip_address)
            
            console.print(summary_table)
            console.print(Panel(f"Total de clientes: [bold]{len(clientes)}[/bold]. Archivo: [yellow]{WG_CONFIG_FILE}[/yellow]", expand=False, border_style="yellow"))
            console.rule()
            needs_refresh = False

        try:
            client_num_str = Prompt.ask(
                f"Introduce el número del cliente para ver/editar detalles (1-{len(clientes)}) o '0' para volver al menú principal"
            )
            if not client_num_str.strip():
                console.print("[yellow]No se ingresó ningún número. Intenta de nuevo.[/yellow]")
                continue

            client_num = int(client_num_str)

            if client_num == 0:
                break # Volver al menú principal
            
            if 1 <= client_num <= len(clientes):
                selected_client_data = clientes[client_num - 1]
                # edit_clients.edit_client_interactive espera el UUID que es la clave en el JSON.
                # list_clients.load_data() lo proporciona como el campo 'uuid'.
                client_uuid_for_edit = selected_client_data.get('uuid')

                if not client_uuid_for_edit:
                    console.print("[red]Error: No se pudo determinar el UUID del cliente para la edición.[/red]")
                    console.print("[dim]Esto puede indicar un problema con la carga de datos desde 'list_clients.py'.[/dim]")
                    continue
                
                edited = display_single_client_details_and_edit_option(selected_client_data, client_num, client_uuid_for_edit)
                if edited:
                    needs_refresh = True # Marcar para recargar la lista de clientes
                # Al volver, el bucle continuará, y si needs_refresh es True, se recargará la tabla.
                # Si no, se volverá a pedir un número.
            else:
                console.print(f"[red]Número de cliente inválido. Debe estar entre 1 y {len(clientes)} o ser 0.[/red]")
        
        except ValueError:
            console.print("[red]Entrada inválida. Por favor, introduce un número.[/red]")
        except Exception as e:
            console.print(f"[bold red]Ocurrió un error inesperado:[/bold red] {e}")

def display_single_client_details_and_edit_option(client_data, client_number, client_uuid):
    """Muestra detalles y ofrece opción de editar. Retorna True si se editó y guardó."""
    console.clear()
    client_name = client_data.get('name', f'Cliente #{client_number}')
    console.print(Panel(f"[bold magenta]Detalles Completos del Cliente: {client_name} (ID: {client_uuid})[/bold magenta]",
                      expand=False, border_style="magenta"))

    details_table = Table(show_header=True, header_style="bold cyan", border_style="green")
    details_table.add_column("Campo", style="dim cyan", width=25)
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

    if Confirm.ask(f"\n¿Deseas editar los datos del cliente '{client_name}'?", default=False):
        changes_made = edit_client_interactive(client_uuid) # Pasar el UUID
        if changes_made:
            console.print("[green]Los datos del cliente han sido actualizados.[/green]")
            Prompt.ask("[dim]Presiona Enter para continuar...[/dim]", default="", show_default=False)
            return True # Indicar que hubo cambios y se guardaron
        else:
            # edit_client_interactive ya imprime mensajes si se cancela o no hay cambios
            Prompt.ask("[dim]Presiona Enter para volver al listado resumen...[/dim]", default="", show_default=False)
            return False # No hubo cambios o se canceló la edición
    else:
        Prompt.ask("\n[dim]Presiona Enter para volver al listado resumen...[/dim]", default="", show_default=False)
        #display_clients()
        return True # No se quiso editar

def prompt_add_new_client():
    console.clear()
    console.print(Panel("[bold green]Añadir Nuevo Cliente[/bold green]", expand=False, border_style="green"))
    client_name_input = Prompt.ask("Introduce el nombre para el nuevo cliente (o deja en blanco para cancelar)")
    
    if client_name_input and client_name_input.strip():
        add_client_add_new_client(client_name_input) 
    elif not client_name_input.strip():
        console.print("[yellow]Operación cancelada. No se añadió ningún cliente.[/yellow]")
    else: 
        console.print("[red]Nombre de cliente inválido. No se añadió ningún cliente.[/red]")
    console.rule(style="dim green")

def main_menu():
    console.clear()
    while True:
        console.print(Panel(
            Text("Gestor de Clientes WireGuard (CLI)", style="bold white on blue", justify="center"),
            title="[bold blue]Menú Principal[/bold blue]",
            border_style="blue",
            padding=(1, 2)
        ))
        console.print("1. [bold green]Listar/Editar[/bold green] clientes")
        console.print("2. [bold yellow]Añadir[/bold yellow] un nuevo cliente")
        console.print("3. [bold cyan]Generar Configuración WG (Servidor)[/bold cyan]")
        console.print("4. [bold red]Salir[/bold red]")
        console.rule(style="dim blue")
        
        choice = Prompt.ask("Selecciona una opción (1-4)", choices=["1", "2", "3", "4"], default="4")
        
        if choice == '1':
            display_clients()
        elif choice == '2':
            prompt_add_new_client()
        elif choice == '3':
            # Llamar al nuevo script gw_conf.py
            script_path = os.path.join(current_dir, "gw_conf.py")
            if not os.path.exists(script_path):
                console.print(f"[bold red]Error:[/bold red] El script '{script_path}' no se encuentra.")
            else:
                try:
                    console.print(f"\n[cyan]Lanzando el generador de configuración del servidor...[/cyan]")
                    # Usar sys.executable para asegurar que se usa el mismo intérprete de Python
                    subprocess.run([sys.executable, script_path], check=True)
                except FileNotFoundError: # Debería ser capturado por el os.path.exists, pero por si acaso
                    console.print(f"[bold red]Error:[/bold red] No se pudo encontrar el intérprete de Python o el script '{script_path}'.")
                except subprocess.CalledProcessError as e:
                    console.print(f"[bold red]Error:[/bold red] El script 'gw_conf.py' terminó con un error (código {e.returncode}).")
                except Exception as e:
                    console.print(f"[bold red]Error inesperado al ejecutar 'gw_conf.py':[/bold red] {e}")
        elif choice == '4':
            console.print("[bold blue]Saliendo del gestor. ¡Hasta luego![/bold blue]")
            break
        
        Prompt.ask("\n[dim]Presiona Enter para volver al menú principal...[/dim]", default="", show_default=False, show_choices=False)
        console.clear()
if __name__ == "__main__":
    if not os.path.exists(WG_CONFIG_FILE):
        console.print(f"[yellow]Advertencia:[/yellow] El archivo de configuración '[bold]{WG_CONFIG_FILE}[/bold]' no existe.")
    
    main_menu()
