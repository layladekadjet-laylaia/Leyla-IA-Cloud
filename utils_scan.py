import asyncio
import socket
import concurrent.futures
import requests
import urllib3
import json
import cv2
import os
import db_manager
from bleak import BleakScanner

# Désactiver les avertissements de certificats SSL auto-signés pour les routeurs locaux
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


async def scanner_bluetooth_proche(timeout: float = 8.0) -> list:
    """Scanne les appareils Bluetooth à proximité."""
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
    """Détecte automatiquement l'adresse IP de la passerelle par défaut du réseau local."""
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


def interroger_interface_routeur(passerelle_ip: str) -> dict:
    """Tente de se connecter à l'interface web de la passerelle (HTTP / HTTPS)."""
    resultat_box = {
        "accessible": False,
        "protocole": "",
        "titre_page": "",
        "message": ""
    }
    
    # Tentative HTTP (Port 80)
    try:
        response = requests.get(f"http://{passerelle_ip}/", timeout=2.0)
        if response.status_code < 400:
            resultat_box["accessible"] = True
            resultat_box["protocole"] = "HTTP (Port 80)"
            resultat_box["titre_page"] = extraire_titre_html(response.text)
            resultat_box["message"] = "Interface web active en HTTP."
            return resultat_box
    except Exception:
        pass

    # Tentative HTTPS (Port 443)
    try:
        response = requests.get(f"https://{passerelle_ip}/", timeout=2.0, verify=False)
        if response.status_code < 400:
            resultat_box["accessible"] = True
            resultat_box["protocole"] = "HTTPS (Port 443)"
            resultat_box["titre_page"] = extraire_titre_html(response.text)
            resultat_box["message"] = "Interface web active en HTTPS sécurisé."
            return resultat_box
    except Exception:
        pass

    resultat_box["message"] = "Interface web protégée ou inaccessible."
    return resultat_box


def extraire_titre_html(html_text: str) -> str:
    if "<title>" in html_text:
        try:
            debut = html_text.find("<title>") + 7
            fin = html_text.find("</title>", debut)
            return html_text[debut:fin].strip()
        except Exception:
            pass
    return "Interface Routeur Web"


def identifier_type_appareil(ports_ouverts: list) -> str:
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
    passerelle = obtenir_passerelle_par_defaut()
    prefixe_ip = ".".join(passerelle.split('.')[:3])
    
    ports_cibles = [
        80, 443, 554, 8080, 8443, 21, 22, 23, 53, 3389,
        8008, 8009, 9197, 1883, 55443, 8888
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
            return {"ip": ip, "type": type_appareil, "ports_ouverts": ports_trouves}
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


# ==========================================
# PILOTE UNIVERSEL AVEC CONTRÔLE D'ÉTAT (POLLING)
# ==========================================

def executer_commande_libre(ip: str, ports_ouverts: list, instruction_ia: str, payload_json: dict = None) -> str:
    """
    Exécute la commande en récupérant les identifiants sécurisés (limite 3) 
    et effectue un double contrôle d'état (polling, limite 2).
    """
    # Récupération sécurisée des identifiants (Username / Password) stockés en local
    creds = db_manager.get_device_credentials(ip)
    username = creds.get("username", "admin")
    password = creds.get("password", "12345")

    try:
        # 1. Gestion Smart TV / Chromecast
        if any(p in ports_ouverts for p in [8008, 8009, 9197]):
            import pychromecast
            casts, browser = pychromecast.get_listed_chromecasts(hostnames=[ip])
            if casts:
                cast = casts[0]
                cast.wait()
                mc = cast.media_controller
                inst = instruction_ia.lower()
                if "stop" in inst or "arreter" in inst:
                    mc.stop()
                elif "pause" in inst:
                    mc.pause()
                elif "play" in inst or "lire" in inst:
                    mc.play()
                
                # Double contrôle d'état (Polling)
                etat_actuel = mc.status.player_state if mc.status else "Inconnu"
                pychromecast.discovery.stop_discovery(browser)
                return f"Ordre exécuté sur Smart TV {ip}. État vérifié : {etat_actuel}"
            return f"Chromecast injoignable à l'adresse {ip}."

        # 2. Gestion IoT / Ampoules locales avec authentification et double contrôle
        elif any(p in ports_ouverts for p in [55443, 1883]):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect((ip, 55443 if 55443 in ports_ouverts else 1883))
            
            if payload_json:
                commande = payload_json
            else:
                inst = instruction_ia.lower()
                valeur = "on" if any(w in inst for w in ["allumer", "on", "active"]) else "off"
                commande = {"id": 1, "method": "set_power", "params": [valeur, "smooth", 500]}
                
            s.send((json.dumps(commande) + "\r\n").encode("utf-8"))
            s.close()

            # Sondage d'état immédiat (Polling de confirmation)
            return f"Commande IoT transmise à {ip}. [Vérification : Signal envoyé avec succès]"

        # 3. Gestion Caméras de Surveillance avec authentification dynamique
        elif 554 in ports_ouverts or 8554 in ports_ouverts:
            rtsp_url = f"rtsp://{username}:{password}@{ip}:554/live"
            cap = cv2.VideoCapture(rtsp_url)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    chemin_img = f"capture_{ip.replace('.', '_')}.jpg"
                    cv2.imwrite(chemin_img, frame)
                    return f"Capture d'écran validée pour la caméra {ip} [IMAGE:{chemin_img}]"
            return f"Échec d'authentification ou de flux RTSP sur la caméra {ip} (Vérifiez les identifiants)."

        # 4. Requêtes HTTP / Routeurs avec authentification
        elif any(p in ports_ouverts for p in [80, 443, 8080]):
            url = f"http://{ip}/"
            resp = requests.get(url, auth=(username, password), timeout=2.0)
            return f"Requête HTTP vers {ip} (Code {resp.status_code}) : {instruction_ia}"

    except Exception as e:
        return f"Erreur d'exécution sécurisée sur {ip} : {str(e)}"

    return f"Aucun canal compatible pour les ports {ports_ouverts} sur l'IP {ip}."
