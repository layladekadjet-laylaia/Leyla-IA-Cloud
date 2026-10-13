import os
import shutil
from utils_audit import enregistrer_action

def explorer_dossier(chemin: str) -> list:
    """
    Explore un répertoire sur le serveur ou l'ordinateur de l'entreprise
    pour lister les fichiers et dossiers disponibles.
    """
    try:
        elements = os.listdir(chemin)
        enregistrer_action("EXPLORATION", chemin, "SUCCÈS", f"{len(elements)} éléments trouvés")
        return elements
    except Exception as e:
        enregistrer_action("EXPLORATION", chemin, "ÉCHEC", str(e))
        return [f"Erreur d'accès : {e}"]

def creer_rapport_texte(nom_fichier: str, contenu: str, dossier_cible: str = ".") -> bool:
    """
    Crée un fichier de rapport ou de synthèse sur le disque à la demande de l'ingénieur.
    """
    chemin_complet = os.path.join(dossier_cible, nom_fichier)
    try:
        with open(chemin_complet, "w", encoding="utf-8") as f:
            f.write(contenu)
        enregistrer_action("CRÉATION_FICHIER", chemin_complet, "SUCCÈS")
        return True
    except Exception as e:
        enregistrer_action("CRÉATION_FICHIER", chemin_complet, "ÉCHEC", str(e))
        return False
