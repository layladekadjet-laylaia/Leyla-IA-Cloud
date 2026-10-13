import asyncio
import socket
import concurrent.futures
from bleak import BleakScanner


async def scanner_bluetooth_proche() -> list:
    """Scanne les appareils Bluetooth à proximité pendant 4 secondes."""
    try:
        devices = await BleakScanner.discover(timeout=4.0)
        resultats = []
        for d in devices:
            nom = d.name if d.name else "Appareil Bluetooth Inconnu"
            resultats.append({"nom": nom, "adresse": d.address, "rssi": d.rssi})
        return resultats
    except Exception as e:
        print(f"Erreur scan Bluetooth : {e}")
        return []


def verifier_appareil_reseau(ip: str, port: int, timeout: float = 0.8) -> bool:
    """Vérifie si une machine ou un service est actif sur le réseau local."""
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
    Scanne rapidement les adresses de la plage IP locale en multi-threading
    pour détecter des caméras (port 554) ou des serveurs Web (ports 80/8080).
    """
    appareils_trouves = []

    def tester_ip(dernier_octet):
        ip = f"{prefixe_ip}.{dernier_octet}"
        for port in ports:
            if verifier_appareil_reseau(ip, port):
                return {"ip": ip, "port_ouvert": port}
        return None

    # Exécution parallèle pour un scan réseau ultra-rapide
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        resultats = executor.map(tester_ip, range(1, 255))
        for res in resultats:
            if res:
                appareils_trouves.append(res)

    return appareils_trouves
