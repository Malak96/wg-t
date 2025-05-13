import json
import os
import uuid
import datetime
import subprocess

WG_CONFIG_FILE = "wg0.json"
IP_SUBNET_PREFIX = "10.10.10." # Asume IPs como 10.10.10.X
IP_START_OCTET = 2
IP_MAX_OCTET = 254

def load_data(file_path):
    """Carga los datos desde el archivo JSON. Si el archivo no existe, devuelve una estructura base."""
    if not os.path.exists(file_path):
        print(f"El archivo '{file_path}' no existe. Se creará uno nuevo con estructura base.")
        return {"clients": {}}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: El archivo '{file_path}' no contiene un JSON válido o está dañado.")
        print("Se procederá con una estructura base en memoria, pero el archivo original no se modificará hasta un guardado exitoso.")
        return {"clients": {}}
    except Exception as e:
        print(f"Ocurrió un error inesperado al cargar '{file_path}': {e}")
        # Podrías decidir terminar aquí o continuar con una estructura vacía
        raise # O return {"clients": {}} si prefieres intentar continuar

def save_data(file_path, data):
    """Guarda los datos en el archivo JSON con formato indentado."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Datos guardados exitosamente en '{file_path}'.")
    except Exception as e:
        print(f"Error al guardar los datos en '{file_path}': {e}")

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
        print("Advertencia: Comando 'wg' no encontrado. Usando placeholders para las claves.")
        print("Por favor, asegúrate de que las herramientas de WireGuard estén instaladas y en el PATH para generar claves reales.")
        return "PLACEHOLDER_PRIVATE_KEY_wg_not_found", "PLACEHOLDER_PUBLIC_KEY_wg_not_found"
    except subprocess.CalledProcessError as e:
        print(f"Error ejecutando el comando 'wg': {e}")
        print("Usando placeholders para las claves.")
        return "PLACEHOLDER_PRIVATE_KEY_wg_error", "PLACEHOLDER_PUBLIC_KEY_wg_error"

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
                print(f"Advertencia: El campo 'address' para el cliente UUID '{client_uuid}' tiene un formato inesperado: {type(client_addresses_field)}. Se omitirá.")

            for addr_cidr in addresses_to_check:
                if isinstance(addr_cidr, str): # Asegurarse de que el elemento sea una cadena antes de hacer split
                    try:
                        ip_part = addr_cidr.split('/')[0] # ej: "10.10.10.2"
                        if ip_part.startswith(prefix):
                            last_octet_str = ip_part.split('.')[-1]
                            if last_octet_str.isdigit():
                                used_octets.add(int(last_octet_str))
                    except (IndexError, ValueError) as e:
                        print(f"Advertencia: No se pudo parsear la dirección IP: '{addr_cidr}'. Error: {e}")
                else:
                    print(f"Advertencia: Elemento no válido en la lista de direcciones para el cliente UUID '{client_uuid}': {addr_cidr}. Se omitirá.")
    
    for octet in range(start_octet, max_octet + 1):
        if octet not in used_octets:
            return f"{prefix}{octet}/32" # Devuelve la IP con CIDR /32
            
    return None # No hay IPs disponibles

def add_new_client(client_name):
    """
    Genera un nuevo cliente, lo añade a los datos cargados y guarda el archivo.
    """
    if not client_name or not client_name.strip():
        print("Error: El nombre del cliente no puede estar vacío.")
        return

    config_data = load_data(WG_CONFIG_FILE)
    if "clients" not in config_data or not isinstance(config_data["clients"], dict):
        print("Error: La estructura del archivo de configuración es incorrecta. Falta la sección 'clients' o no es un diccionario.")
        print("Creando sección 'clients' vacía.")
        config_data["clients"] = {}

    # Generar datos para el nuevo cliente
    client_uuid = str(uuid.uuid4())
    private_key, public_key = generate_wg_keys()
    
    next_ip = get_next_available_ip(config_data.get("clients"), IP_SUBNET_PREFIX, IP_START_OCTET, IP_MAX_OCTET)
    if not next_ip:
        print(f"Error: No hay direcciones IP disponibles en la subred {IP_SUBNET_PREFIX}{IP_START_OCTET}-{IP_MAX_OCTET}.")
        return

    timestamp = datetime.datetime.utcnow().isoformat(timespec='milliseconds') + "Z"

    new_client_data = {
        "id": client_uuid,
        "name": client_name.strip(),
        "address": next_ip, # Guardar como cadena de texto
        "privateKey": private_key,
        "publicKey": public_key,
        "presharedKey": None, # Puedes implementar la generación de PSK si es necesario
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "endpoint": "", # Generalmente se configura en el cliente, no en el servidor para este campo
        "dns": "", # Puedes poner aquí tus servidores DNS, ej: "1.1.1.1" o ["1.1.1.1", "8.8.8.8"]
        "persistentKeepalive": "25", # Un valor común
        "allowedIPs": "0.0.0.0/0, ::/0", # Guardar como cadena de texto
        "enabled": True
    }

    # Añadir el nuevo cliente
    config_data["clients"][client_uuid] = new_client_data
    print(f"\nCliente '{client_name}' preparado para ser añadido con UUID: {client_uuid} e IP: {next_ip}")

    # Guardar los datos actualizados
    save_data(WG_CONFIG_FILE, config_data)
    
    print("\nDetalles del cliente añadido:")
    for key, value in new_client_data.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    # Ejemplo de uso:
    client_name_input = input("Introduce el nombre para el nuevo cliente: ")
    if client_name_input:
        add_new_client(client_name_input)
    else:
        print("No se introdujo un nombre. No se añadió ningún cliente.")

    # Para añadir múltiples clientes, podrías llamar a add_new_client en un bucle
    # o modificar la función para aceptar una lista de nombres.
    # Ejemplo:
    # add_new_client("MiLaptop")
    # add_new_client("TelefonoDeTrabajo")

    # Para verificar, puedes usar el script de listado de clientes que ya tienes.