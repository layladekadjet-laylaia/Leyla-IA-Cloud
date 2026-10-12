import asyncio
import socket
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
