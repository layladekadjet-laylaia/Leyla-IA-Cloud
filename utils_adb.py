import subprocess
import shutil

def verifier_adb() -> bool:
    """Vérifie si le binaire ADB est accessible dans le PATH système."""
    return shutil.which("adb") is not None

def exécuter_commande_adb(commande: str) -> str:
    """Exécute une commande adb shell et retourne le résultat ou l'erreur."""
    if not verifier_adb():
        return "Erreur : Le binaire 'adb' n'est pas détecté dans le PATH du système, Mon Professeur."

    try:
        cmd = f"adb {commande}"
        resultat = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        if resultat.returncode == 0:
            return resultat.stdout.strip() or "Commande exécutée avec succès."
        else:
            return f"Erreur ADB : {resultat.stderr.strip()}"
    except Exception as e:
        return f"Exception lors de l'exécution ADB : {str(e)}"

def lister_appareils_adb() -> str:
    """Liste les appareils Android connectés."""
    return exécuter_commande_adb("devices")

def gerer_lampe_torche(action: str = "on") -> str:
    """
    Tente d'allumer ou éteindre la lampe torche.
    action: 'on' ou 'off'
    """
    etat = "1" if action.lower() == "on" else "0"
    
    # Tentative 1 : Via Termux:API (méthode sans root la plus directe si installée)
    cmd_termux = f"shell termux-torch {action.lower()}"
    res = exécuter_commande_adb(cmd_termux)
    if "not found" not in res.lower() and "erreur" not in res.lower():
        return f"Lampe torche ({action.upper()}) via Termux:API, Mon Professeur."

    # Tentative 2 : Via modification directe des nœuds sysfs (requiert root sur certains MediaTek/Android)
    chemins_led = [
        "/sys/class/leds/led:torch_0/brightness",
        "/sys/class/leds/flashlight/brightness",
        "/sys/class/camera/flash/rear_flash"
    ]
    
    valeur_luminosite = "255" if action.lower() == "on" else "0"
    for chemin in chemins_led:
        cmd_root = f"shell \"su -c 'echo {valeur_luminosite} > {chemin}'\""
        res_root = exécuter_commande_adb(cmd_root)
        if "Permission denied" not in res_root and "No such file" not in res_root and "Erreur" not in res_root:
            return f"Lampe torche ({action.upper()}) activée via node sysfs {chemin}, Mon Professeur."

    return "Impossible de basculer la lampe torche automatiquement sans privilèges Root ou sans Termux:API sur l'appareil connecté."


# Test rapide du script
if __name__ == "__main__":
    print("--- Vérification des appareils connectés ---")
    print(lister_appareils_adb())
