import os
import uuid
import platform
import hashlib
import requests
import toml

def obtenir_device_id() -> str:
    """
    Génère une empreinte matérielle unique et stable pour le PC local,
    basée sur les informations système de la machine.
    """
    # On combine le nom de l'hôte, le processeur et le système
    infos_systeme = f"{platform.node()}-{platform.processor()}-{platform.system()}"
    device_id = hashlib.sha256(infos_systeme.encode('utf-8')).hexdigest()
    return device_id

def charger_config_supabase() -> tuple:
    """Charge l'URL et la clé anonyme depuis le fichier config.toml local."""
    if not os.path.exists("config.toml"):
        raise FileNotFoundError("❌ Fichier config.toml introuvable à la racine du projet.")
    
    config = toml.load("config.toml")
    url = config["supabase"]["url"]
    key = config["supabase"]["key"]
    return url, key

def verifier_licence_et_recuperer_secrets() -> tuple[bool, str]:
    """
    Vérifie l'authenticité de la licence du poste auprès de Supabase
    et récupère la clé Gemini sécurisée si l'accès est autorisé.
    
    Retourne : (True/False, cle_gemini_ou_message_erreur)
    """
    try:
        supabase_url, supabase_key = charger_config_supabase()
        device_id = obtenir_device_id()
        print(f"💻 Empreinte de l'appareil (Device ID) : {device_id[:12]}...")

        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }

        # 1. Vérifier si ce device_id est enregistré et lié à une entreprise active
        url_licence = f"{supabase_url}/rest/v1/licences_postes?device_id=eq.{device_id}&select=*,entreprises(*)"
        response = requests.get(url_licence, headers=headers, timeout=10)

        if response.status_code != 200:
            return False, f"Erreur de communication avec le serveur de licence (Code {response.status_code})."

        data = response.json()
        if not data:
            return False, "❌ Ce poste n'est pas enregistré. Veuillez contacter l'administrateur."

        poste_info = data[0]
        entreprise = poste_info.get("entreprises")

        if not entreprise or entreprise.get("statut") != "actif":
            return False, "⛔ L'abonnement de cette entreprise est expiré ou suspendu."

        print(f"✅ Entreprise reconnue : {entreprise.get('nom_entreprise')}")

        # 2. Si la licence est valide, récupérer la clé secrète Gemini depuis la table secrets_systeme
        url_secrets = f"{supabase_url}/rest/v1/secrets_systeme?cle_nom=eq.GOOGLE_GEMINI_API_KEY&select=cle_valeur"
        resp_secret = requests.get(url_secrets, headers=headers, timeout=10)

        if resp_secret.status_code == 200 and resp_secret.json():
            gemini_key = resp_secret.json()[0].get("cle_valeur")
            return True, gemini_key
        else:
            return False, "⚠️ Clé secrète introuvable sur le serveur distant."

    except requests.exceptions.RequestException as e:
        return False, f"🌐 Erreur réseau : impossible de joindre le serveur de licence. ({e})"
    except Exception as ex:
        return False, f"⚠️ Erreur système inattendue : {ex}"
