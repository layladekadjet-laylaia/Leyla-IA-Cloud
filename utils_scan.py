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
    Détecte automatiquement l'adresse IP de la passerelle par défaut du réseau local.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_locale = s.getsockname()[0]
        s.close()
        
        octets = ip_locale.split('.')
        return f"{octets[0]}.{octets[1]}.{octets[2]}.1"
    except Exception:
        return "192.168.1.1"


def verifier_appareil_reseau(ip: str, port: int, timeout: float = 0.5) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        resultat = sock.connect_ex((ip, port))
        sock.close()
        return resultat == 0
    except Exception:
        return False


def identifier_type_appareil(ports_ouverts: list) -> str:
    """
    Classe l'appareil selon les ports ouverts détectés.
    """
    if 554 in ports_ouverts or 8554 in ports_ouverts:
        return "📹 Caméra de Surveillance"
    elif 8008 in ports_ouverts or 8009 in ports_ouverts or 9197 in ports_ouverts:
        return "📺 Smart TV / Chromecast"
    elif 55443 in ports_ouverts or 1883 in ports_ouverts:
        return "💡 Ampoule / Prise Connectée (IoT)"
    elif 3389 in ports_ouverts or 22 in ports_ouverts:
        return "💻 Ordinateur / Serveur / Passerelle Secondaire"
    elif 80 in ports_ouverts or 443 in ports_ouverts or 8080 in ports_ouverts:
        return "🌐 Routeur / Interface Web / Box"
    else:
        return "🔌 Appareil Connecté Divers"


def scanner_reseau_complet() -> dict:
    """
    Scanne la passerelle et tous les appareils du réseau, les classe
    et retourne un inventaire structuré pour Leyla.
    """
    passerelle = obtenir_passerelle_par_defaut()
    prefixe_ip = ".".join(passerelle.split('.')[:3])
    
    ports_cibles = [
        80, 443, 554, 8080, 8443,  # Web & Vidéo
        21, 22, 23, 53, 3389,      # Admin & Réseau
        8008, 8009, 9197,          # Smart TV
        1883,                      # MQTT IoT
        55443,                     # Ampoules / Prises locales
        8888                       # Passerelles alternatives
    ]

    appareils_decouverts = []

    def tester_ip(dernier_octet):
        ip = f"{prefixe_ip}.{dernier_octet}"
        ports_trouves = []
        for port in ports_cibles:
            if verifier_appareil_reseau(ip, port, timeout=0.4):
                ports_trouves.append(port)
        if ports_trouves:
            type_appareil = identifier_type_appareil(ports_trouves)
            return {
                "ip": ip,
                "type": type_appareil,
                "ports_ouverts": ports_trouves
            }
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
        resultats = executor.map(tester_ip, range(1, 255))
        for res in resultats:
            if res:
                appareils_decouverts.append(res)

    return {
        "passerelle": passerelle,
        "total_appareils": len(appareils_decouverts),
        "appareils": appareils_decouverts
    }
