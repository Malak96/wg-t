import uuid
import json 
import os

wg_file = "wg0.json"
def load_data():
    """Carga los datos de todos los clientes desde el archivo JSON.
    Devuelve una lista de diccionarios, donde cada diccionario representa un cliente
    e incluye su UUID (la clave original del diccionario de clientes).
    """
    if not os.path.exists(wg_file):
        print(f"Advertencia: El archivo '{wg_file}' no existe. No se pueden cargar clientes.")
        return [] # Si el archivo no existe, no hay clientes
    try:
        with open(wg_file, 'r', encoding='utf-8') as f:
            data_from_file = json.load(f)
        
        # Asumimos que "clients" es una clave en el JSON raíz
        # y su valor es un diccionario {uuid: client_details}.
        clients_dict = data_from_file.get("clients")
        
        if clients_dict is None:
            print(f"Error: La clave 'clients' no se encuentra en '{wg_file}' o el contenido es nulo.")
            return []
        
        if not isinstance(clients_dict, dict):
            print(f"Error: La sección 'clients' en '{wg_file}' no es un diccionario como se esperaba.")
            return []
            
        processed_clients = []
        for client_uuid, client_info in clients_dict.items():
            if isinstance(client_info, dict):
                # Crear un nuevo diccionario para cada cliente, añadiendo su UUID (la clave del diccionario).
                current_client_data = {'uuid': client_uuid} 
                current_client_data.update(client_info) # Añadir todos los demás campos del cliente
                processed_clients.append(current_client_data)
            else:
                print(f"Advertencia: Los datos para el cliente UUID '{client_uuid}' no tienen el formato esperado (diccionario) y serán omitidos.")
        
        return processed_clients

    except json.JSONDecodeError:
        print(f"Error: El archivo '{wg_file}' no contiene un JSON válido o está vacío.")
        return []
    except Exception as e: # Captura más genérica para otros errores de lectura o procesamiento
        print(f"Ocurrió un error inesperado al leer o procesar el archivo '{wg_file}': {e}")
        return []
    

if __name__ == "__main__":
    clientes = load_data()
    if clientes:
        print("\nListado de Clientes y sus campos:")
        print("------------------------------------")
        for i, cliente_data in enumerate(clientes):
            print(f"\nCliente #{i + 1}:")
            for campo, valor in cliente_data.items():
                # Formateamos el nombre del campo para mejor legibilidad
                nombre_campo_formateado = str(campo).replace('_', ' ').capitalize()
                print(f"  {nombre_campo_formateado}: {valor}")
            if i < len(clientes) - 1: # Añadir separador entre clientes, excepto para el último
                print("---")
        print("------------------------------------")
    else:
        # Este mensaje se mostrará si load_data devuelve una lista vacía (ej. archivo no encontrado, error de formato, etc.)
        print("No se encontraron datos de clientes para mostrar o se produjo un error durante la carga.")
