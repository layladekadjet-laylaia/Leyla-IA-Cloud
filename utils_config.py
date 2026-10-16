import os
import sys
import toml

def charger_configuration():
    """Charge les paramètres depuis le fichier config.toml de manière robuste (mode normal ou exécutable PyInstaller)."""
    chemins_possibles = []
    
    # Si on tourne dans l'exécutable PyInstaller
    if getattr(sys, "frozen", False):
        # 1. Chercher d'abord à côté du fichier .exe (permet à l'utilisateur de modifier la config)
        chemins_possibles.append(os.path.join(os.path.dirname(sys.executable), "config.toml"))
        # 2. Chercher ensuite dans le dossier temporaire embarqué
        chemins_possibles.append(os.path.join(sys._MEIPASS, "config.toml"))
    else:
        # En mode développement normal
        chemins_possibles.append("config.toml")
    
    chemin_config = None
    for p in chemins_possibles:
        if os.path.exists(p):
            chemin_config = p
            break
            
    if not chemin_config:
        raise FileNotFoundError("❌ Fichier de configuration 'config.toml' introuvable.")
    
    with open(chemin_config, "r", encoding="utf-8") as f:
        return toml.load(f)

# Utilisation rapide :
config = charger_configuration()
SUPABASE_URL = config["supabase"]["url"]
SUPABASE_KEY = config["supabase"]["key"]
