import toml
import os

def charger_configuration():
    """Charge les paramètres depuis le fichier config.toml local."""
    chemin_config = "config.toml"
    if not os.path.exists(chemin_config):
        raise FileNotFoundError("❌ Fichier de configuration introuvable.")
    
    with open(chemin_config, "r", encoding="utf-8") as f:
        return toml.load(f)

# Utilisation rapide :
config = charger_configuration()
SUPABASE_URL = config["supabase"]["url"]
SUPABASE_KEY = config["supabase"]["key"]
