import asyncio
import socket
import concurrent.futures
from bleak import BleakScanner


async def scanner_bluetooth_proche(timeout: float = 8.0) -> list:
    """
    Scanne les appareils Bluetooth à proximité.
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


def obtenir_passerelle_par_defaut() -> str:
    """
    Détecte automatiquement l'adresse IP de la passerelle par défaut du réseau local,
    s'adaptant ainsi à n'importe quelle entreprise cliente sans codage en dur.
    """
    try:
        # Crée une socket temporaire pour trouver l'IP locale connectée au web/réseau
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_locale = s.getsockname()[0]
        s.close()
        
        # Extrait le préfixe réseau (ex: '192.168.1' à partir de '192.168.1.55')
        octets = ip_locale.split('.')
        passerelle_estimee = f"{octets[0]}.{octets[1]}.{octets[2]}.1"
        return passerelle_estimee
    except Exception:
        # Fallback universel par défaut si la détection échoue
        return "192.168.1.1"


def verifier_appareil_reseau(ip: str, port: int, timeout: float = 1.5) -> bool:
    """
    Vérifie si une machine ou un service est actif sur le réseau local.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        resultat = sock.connect_ex((ip, port))
        sock.close()
        return resultat == 0
    except Exception:
        return False


def scanner_plage_ip_locale(ports: list = [80, 554, 8080]) -> list:
    """
    Scanne dynamiquement la plage IP du réseau actuel de l'entreprise.
    """
    passerelle = obtenir_passerelle_par_defaut()
    prefixe_ip = ".".join(passerelle.split('.')[:3])
    
    appareils_trouves = []

    def tester_ip(dernier_octet):
        ip = f"{prefixe_ip}.{dernier_octet}"
        for port in ports:
            if verifier_appareil_reseau(ip, port, timeout=1.0):
                return {"ip": ip, "port_ouvert": port}
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        resultats = executor.map(tester_ip, range(1, 255))
        for res in resultats:
            if res:
                appareils_trouves.append(res)

    return appareils_trouves
