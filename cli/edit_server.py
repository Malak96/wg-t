import os
import json
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

WG_CONFIG_FILE = "wg0.json"
console = Console()

def load_server_config():
    """Carga la configuración del servidor desde el archivo JSON."""
    if not os.path.exists(WG_CONFIG_FILE):
        console.print(f"[bold red]Error:[/bold red] El archivo '{WG_CONFIG_FILE}' no existe.")
        return None
    try:
        with open(WG_CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("server", {})
    except json.JSONDecodeError:
        console.print(f"[bold red]Error:[/bold red] El archivo '{WG_CONFIG_FILE}' no contiene un JSON válido.")
        return None
    except Exception as e:
        console.print(f"[bold red]Error inesperado al cargar '{WG_CONFIG_FILE}':[/bold red] {e}")
        return None

def save_server_config(server_config):
    """Guarda la configuración del servidor en el archivo JSON."""
    try:
        with open(WG_CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data["server"] = server_config
        with open(WG_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]Configuración del servidor guardada exitosamente en '{WG_CONFIG_FILE}'.[/green]")
    except Exception as e:
        console.print(f"[bold red]Error al guardar la configuración del servidor:[/bold red] {e}")

def edit_server_config():
    """Permite al usuario editar la configuración del servidor."""
    server_config = load_server_config()
    if not server_config:
        return

    editable_fields = {
        "1": {"key": "address", "prompt": "Nueva dirección IP completa con máscara (ej: 10.0.10.1/24)"},
        "2": {"key": "dns", "prompt": "Nuevo servidor DNS (ej: 1.1.1.1,8.8.8.8)"},
        "3": {"key": "port", "prompt": "Nuevo puerto (ej: 51820)"},
        "4": {"key": "endpoint", "prompt": "Nuevo endpoint (ej: myserver.com)"},
        "5": {"key": "persistentKeepalive", "prompt": "Nuevo valor de Persistent Keepalive (ej: 25 o 0 para desactivar)"}
    }

    while True:
        console.clear()
        console.print(Panel("[bold cyan]Editar Configuración del Servidor[/bold cyan]", border_style="cyan"))

        for opt, field_info in editable_fields.items():
            key = field_info["key"]
            current_value = server_config.get(key, "[italic dim]No establecido[/italic dim]")
            console.print(f"[{opt}] {key.capitalize()}: {current_value}")

        console.print("[S] Guardar y salir")
        console.print("[C] Cancelar cambios y volver a la vista de datos")

        choice = Prompt.ask("Selecciona una opción", choices=list(editable_fields.keys()) + ["S", "s", "C", "c"], default="C").upper()

        if choice == "C":
            # No imprimir mensaje, simplemente volver a la vista de datos
            return False  # Indica que no se guardó nada, solo cancelar y volver

        if choice == "S":
            save_server_config(server_config)
            return True  # Indica que se guardó

        field_key = editable_fields[choice]["key"]
        prompt_text = editable_fields[choice]["prompt"]
        new_value = Prompt.ask(prompt_text, default=str(server_config.get(field_key, "")))

        if field_key == "port" or field_key == "persistentKeepalive":
            try:
                server_config[field_key] = int(new_value)
            except ValueError:
                console.print(f"[red]Valor inválido para {field_key}. Debe ser un número.[/red]")
        else:
            server_config[field_key] = new_value

def view_server_config():
    """Muestra la configuración del servidor y permite editarla o volver al menú principal."""
    server_config = load_server_config()
    if not server_config:
        return

    while True:
        console.clear()
        console.print(Panel("[bold cyan]Configuración Actual del Servidor[/bold cyan]", border_style="cyan"))

        # Mostrar la configuración en una tabla detallada
        from rich.table import Table
        table = Table(title="[bold]Detalles del Servidor WireGuard[/bold]", show_header=True, header_style="bold magenta")
        table.add_column("Campo", style="cyan", no_wrap=True)
        table.add_column("Valor", style="white")
        for key, value in server_config.items():
            display_value = str(value) if value is not None else "[italic dim]No establecido[/italic dim]"
            table.add_row(key, display_value)
        console.print(table)

        console.print("\n[bold cyan]Opciones:[/bold cyan]")
        console.print("1. [green]Editar configuración del servidor[/green]")
        console.print("2. [red]Volver al menú principal[/red]")

        choice = Prompt.ask("Selecciona una opción", choices=["1", "2"], default="2").strip().lower()

        if choice == "2":
            return

        if choice == "1":
            edited = edit_server_config()
            if edited:
                # Si se guardó, recargar datos y mostrar mensaje
                server_config = load_server_config()
                console.clear()
                console.print("[green]Configuración del servidor actualizada exitosamente.[/green]")
                Prompt.ask("[dim]Presiona Enter para continuar...[/dim]", default="", show_default=False)
            # Si se canceló, simplemente se vuelve a mostrar la vista de datos

if __name__ == "__main__":
    view_server_config()