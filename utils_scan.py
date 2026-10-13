import asyncio
import socket
import concurrent.futures
from bleak import BleakScanner


async def scanner_bluetooth_proche(timeout: float = 8.0) -> list:
    """
    Scanne les appareils Bluetooth à proximité.
    Timeout augmenté à 8.0 secondes pour détecter les capteurs IoT plus lents.
    """
    try:
        devices = await BleakScanner.discover(timeout=timeout)
        resultats = []
        for d in devices:
            nom = d.name if d.name else "Appareil Bluetooth Inconnu"
            resultats.append({"nom": nom, "adresse": d.address, "rssi": d.rssi})
        return resultats
    except Exception as e:
        print(f"Erreur scan Bluetooth : {e}")
        return []


def verifier_appareil_reseau(ip: str, port: int, timeout: float = 1.5) -> bool:
    """
    Vérifie si une machine ou un service est actif sur le réseau local.
    Timeout ajusté à 1.5s pour tolérer les variations de latence Wi-Fi.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        resultat = sock.connect_ex((ip, port))
        sock.close()
        return resultat == 0
    except Exception:
        return False


def scanner_plage_ip_locale(prefixe_ip: str = "192.168.1", ports: list = [80, 554, 8080]) -> list:
    """
    Scanne rapidement les adresses de la plage IP locale en multi-threading.
    """
    appareils_trouves = []

    def tester_ip(dernier_octet):
        ip = f"{prefixe_ip}.{dernier_octet}"
        for port in ports:
            if verifier_appareil_reseau(ip, port, timeout=1.2):
                return {"ip": ip, "port_ouvert": port}
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        resultats = executor.map(tester_ip, range(1, 255))
        for res in resultats:
            if res:
                appareils_trouves.append(res)

    return appareils_trouves
