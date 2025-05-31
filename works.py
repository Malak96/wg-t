import subprocess
import ipaddress

def generate_keys():
    """Genera una clave privada y su correspondiente clave pública."""
    try:
        private_key = subprocess.check_output(['wg', 'genkey']).decode('utf-8').strip()
        public_key = subprocess.check_output(['wg', 'pubkey'], input=private_key.encode('utf-8')).decode('utf-8').strip()
        return private_key, public_key
    except FileNotFoundError:
        return "PLACEHOLDER_PRIVATE_KEY_wg_not_found", "PLACEHOLDER_PUBLIC_KEY_wg_not_found"
    except subprocess.CalledProcessError as e:
        return "PLACEHOLDER_PRIVATE_KEY_wg_error", "PLACEHOLDER_PUBLIC_KEY_wg_error"
    
def generate_preshared_key():
    """Genera una clave precompartida (PresharedKey) de WireGuard usando 'wg genpsk'."""
    try:
        psk_proc = subprocess.run(['wg', 'genpsk'], capture_output=True, text=True, check=True, encoding='utf-8')
        return psk_proc.stdout.strip()
    except FileNotFoundError:
        return "no_wg"
    except subprocess.CalledProcessError as e:
        return "error"
    
def get_next_available_ip(clients_data, server_address):
    """Obtiene la siguiente dirección IP disponible en la subred especificada por el servidor."""
    try:
        # Crear el objeto de red a partir de la dirección del servidor
        network = ipaddress.ip_network(server_address, strict=False)
        server_ip = ipaddress.ip_address(server_address.split('/')[0])  # Extraer solo la IP del servidor
    except ValueError:
        return "Server_Invalid_IP"

    used_ips = set()
    if clients_data:
        for client_details in clients_data.values():
            client_address = client_details.get("address")
            if client_address:
                try:
                    ip = ipaddress.ip_address(client_address.split('/')[0])  # Extraer solo la IP
                    used_ips.add(ip)
                except ValueError:
                    return "Client_Invalid_IP"
                   

    # Iterar sobre todas las IPs posibles en la subred, excluyendo la del servidor
    for ip in network.hosts():
        if ip != server_ip and ip not in used_ips:
            return f"{ip}/32"  # Devuelve la IP con máscara /32

    return None 