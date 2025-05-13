
import os
import sys
import json
import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
except ImportError:
    print("La biblioteca 'rich' no está instalada. Por favor, instálala con: pip install rich")
    sys.exit(1)

console = Console()

# Definición de WG_CONFIG_FILE (debe ser consistente con tus otros scripts)
# Si lo tienes en add_client.py, podrías importarlo, pero para mantenerlo simple aquí:
WG_CONFIG_FILE = "wg0.json"

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

def save_config_data(data):
    """Guarda los datos completos en el archivo JSON de configuración."""
    try:
        with open(WG_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]Datos guardados exitosamente en '{WG_CONFIG_FILE}'.[/green]")
        return True
    except Exception as e:
        console.print(f"[bold red]Error al guardar los datos en '{WG_CONFIG_FILE}':[/bold red] {e}")
        return False

def edit_client_interactive(client_uuid_to_edit):
    """
    Permite al usuario editar interactivamente los campos de un cliente específico.
    Retorna True si se realizaron y guardaron cambios, False en caso contrario.
    """
    config_data = load_config_data()
    if not config_data or "clients" not in config_data:
        console.print("[red]No se pudo cargar la configuración de clientes o tiene un formato incorrecto.[/red]")
        return False

    if client_uuid_to_edit not in config_data["clients"]:
        console.print(f"[red]Error: Cliente con UUID '{client_uuid_to_edit}' no encontrado.[/red]")
        return False

    client_to_edit = config_data["clients"][client_uuid_to_edit]

    # Crear una copia de los datos del cliente SIN 'updatedAt' para la comparación de cambios.
    # Esto asegura que solo los cambios en los datos reales del cliente activen un guardado.
    original_client_comparable_data = client_to_edit.copy()
    original_client_comparable_data.pop("updatedAt", None) # Quitar updatedAt para la comparación base
    original_client_comparable_str = json.dumps(original_client_comparable_data, sort_keys=True)

    editable_client = json.loads(json.dumps(client_to_edit)) # Copia profunda de trabajo

    editable_fields = {
        "1": {"key": "name", "prompt": "Nuevo nombre"},
        "2": {"key": "dns", "prompt": "Nuevos DNS (separados por coma, ej: 1.1.1.1,8.8.8.8 o dejar vacío para ninguno)"},
        "3": {"key": "address", "prompt": "Nueva Dirección IP (ej: 10.10.10.X/32)"},
        "4": {"key": "persistentKeepalive", "prompt": "Nuevo Persistent Keepalive (ej: 25 o 0 para desactivar)"},
        "5": {"key": "enabled", "prompt": "Habilitado (s/n)"}
        # La opción de eliminar se manejará por separado en el menú de acciones.
    }

    made_changes = False # Flag para indicar si el usuario intentó hacer algún cambio en un campo

    while True:
        console.clear()
        console.print(Panel(f"[bold yellow]Editando Cliente: {editable_client.get('name', client_uuid_to_edit)}[/bold yellow]",
                          border_style="yellow", expand=False))
        
        current_values_table = Table(title="Valores Actuales y Opciones de Edición", show_header=False, box=None)
        current_values_table.add_column("Opción", style="cyan")
        current_values_table.add_column("Campo", style="green")
        current_values_table.add_column("Valor Actual", style="white")

        for opt, field_info in editable_fields.items():
            key = field_info["key"]
            value = editable_client.get(key)
            if isinstance(value, list):
                display_value = ", ".join(value) if value else "[italic dim]Ninguno[/italic dim]"
            elif value is None:
                display_value = "[italic dim]No establecido[/italic dim]"
            else:
                display_value = str(value)
            current_values_table.add_row(f"[{opt}]", field_info["key"].capitalize(), display_value)
        
        current_values_table.add_row("---", "------------------", "------------------")
        current_values_table.add_row("[S]", "Guardar Cambios y Volver", "")
        current_values_table.add_row("[D]", "Eliminar este Cliente", "")
        current_values_table.add_row("[C]", "Cancelar Cambios y Volver", "")
        console.print(current_values_table)

        choice = Prompt.ask("Selecciona un campo para editar, [S] Guardar, [D] Eliminar, o [C] Cancelar", 
                            choices=[str(k) for k in editable_fields.keys()] + ["S", "s", "D", "d", "C", "c"],
                            default="C").upper()

        if choice == "C":
            if made_changes:
                if Confirm.ask("[yellow]Tienes cambios sin guardar. ¿Estás seguro de que quieres cancelar y perder los cambios?", default=False):
                    console.print("[yellow]Cambios cancelados.[/yellow]")
                    return False
                else:
                    continue # Volver al menú de edición
            else:
                console.print("[yellow]Edición cancelada. No se realizaron cambios.[/yellow]")
                return False # No se hicieron cambios o se cancelaron

        elif choice == "S":
            # Preparar la versión actual de editable_client para comparación (sin updatedAt)
            current_editable_comparable_data = editable_client.copy()
            current_editable_comparable_data.pop("updatedAt", None)
            current_editable_comparable_str = json.dumps(current_editable_comparable_data, sort_keys=True)

            if current_editable_comparable_str == original_client_comparable_str:
                console.print("[yellow]No se detectaron cambios para guardar.[/yellow]")
                if not Confirm.ask("¿Deseas continuar editando?", default=True):
                    return False # Salir sin guardar
                else:
                    continue # Volver al menú de edición
            
            # Si hay cambios reales, actualizar 'updatedAt' y proceder a guardar
            editable_client["updatedAt"] = datetime.datetime.utcnow().isoformat(timespec='milliseconds') + "Z"
            config_data["clients"][client_uuid_to_edit] = editable_client
            if save_config_data(config_data):
                console.print("[green]Cliente actualizado exitosamente.[/green]")
                return True # Cambios guardados
            else:
                console.print("[red]Error al guardar los cambios. Los cambios no se han aplicado.[/red]")
                return False # Error al guardar

        elif choice == "D":
            client_name_display = editable_client.get('name', client_uuid_to_edit)
            if Confirm.ask(f"[bold red]¿Estás ABSOLUTAMENTE SEGURO de que quieres eliminar al cliente '{client_name_display}' ({client_uuid_to_edit})?[/bold red]\nEsta acción no se puede deshacer.", default=False):
                del config_data["clients"][client_uuid_to_edit]
                if save_config_data(config_data):
                    console.print(f"[green]Cliente '{client_name_display}' eliminado exitosamente.[/green]")
                    return True # Indicar que se hizo un cambio (eliminación) y se guardó
                else:
                    console.print("[red]Error al guardar los cambios después de intentar eliminar el cliente. El cliente podría no haber sido eliminado del archivo.[/red]")
                    # Recargar los datos para asegurar la consistencia del estado en memoria si el guardado falló
                    config_data = load_config_data() 
                    return False # Error al guardar
            else:
                console.print("[yellow]Eliminación cancelada.[/yellow]")
                continue # Volver al menú de edición

        elif choice in editable_fields:
            field_key = editable_fields[choice]["key"]
            prompt_text = editable_fields[choice]["prompt"]
            current_value = editable_client.get(field_key)

            # Guardar el valor serializado del campo ANTES de cualquier modificación
            old_field_value_json = json.dumps(current_value)

            new_value_str = Prompt.ask(f"{prompt_text} (actual: {current_value if current_value is not None else 'No establecido'})")
            
            try:
                if field_key == "name":
                    if new_value_str.strip():
                        editable_client[field_key] = new_value_str.strip()
                    else:
                        console.print("[red]El nombre no puede estar vacío.[/red]")
                elif field_key == "dns":
                    cleaned_dns_str = new_value_str.strip()
                    if cleaned_dns_str:
                        editable_client[field_key] = cleaned_dns_str
                    else:
                        editable_client[field_key] = None
                elif field_key == "address":
                    if new_value_str.strip():
                        editable_client[field_key] = new_value_str.strip()
                    else:
                        console.print("[red]La dirección no puede estar vacía.[/red]")
                elif field_key == "persistentKeepalive":
                    cleaned_value = new_value_str.strip()
                    if not cleaned_value or cleaned_value == "0":
                        editable_client[field_key] = 0 
                    else:
                        value_as_int = int(cleaned_value) 
                        if value_as_int < 0:
                            console.print("[red]Persistent Keepalive debe ser un entero no negativo.[/red]")
                        else:
                            editable_client[field_key] = value_as_int # Guardar como entero
                elif field_key == "enabled":
                    if new_value_str.lower() in ['s', 'si', 'true', '1', 'y', 'yes']:
                        editable_client[field_key] = True
                    elif new_value_str.lower() in ['n', 'no', 'false', '0']:
                        editable_client[field_key] = False
                    else:
                        console.print("[red]Valor inválido para 'Habilitado'. Usa s/n.[/red]")
                
                # Comprobar si el valor del campo realmente cambió después de la operación
                new_field_value_json = json.dumps(editable_client.get(field_key))
                if old_field_value_json != new_field_value_json:
                    made_changes = True # Se intentó un cambio que resultó en un valor diferente para este campo

            except ValueError:
                console.print(f"[red]Valor inválido para {field_key}. Intenta de nuevo.[/red]")
            except Exception as e:
                console.print(f"[bold red]Error procesando la entrada:[/bold red] {e}")
        else:
            console.print("[red]Opción no válida.[/red]")

if __name__ == '__main__':
    # Para pruebas directas de edit_clients.py
    console.print("[bold]Modo de prueba para edit_clients.py[/bold]")
    config = load_config_data()
    if config and config.get("clients"):
        clients_dict = config["clients"]
        if clients_dict:
            test_uuid = list(clients_dict.keys())[0] # Tomar el primer UUID para probar
            console.print(f"Intentando editar cliente con UUID: {test_uuid}")
            edit_client_interactive(test_uuid)
        else:
            console.print("[yellow]No hay clientes en el archivo de configuración para probar la edición.[/yellow]")
    else:
        console.print("[yellow]No se pudo cargar la configuración o no hay clientes para probar.[/yellow]")
