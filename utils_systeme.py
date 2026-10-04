import os
import shutil
import subprocess
import json
from typing import List, Dict, Optional

# --- 1. GESTION ILLIMITÉE DES FICHIERS ET DOSSIERS (ACCÈS SYSTÈME TOTAL) ---

def lister_fichiers(chemin_dossier: str = ".") -> str:
    """Liste tous les fichiers et dossiers dans n'importe quel répertoire de l'ordinateur ou du serveur."""
    chemin_abs = os.path.abspath(chemin_dossier)
    
    if not os.path.exists(chemin_abs):
        return f"Erreur : Le dossier '{chemin_abs}' n'existe pas, Mon Professeur."
        
    try:
        fichiers = os.listdir(chemin_abs)
        return json.dumps({
            "dossier_actuel": chemin_abs,
            "contenu": fichiers
        }, ensure_ascii=False)
    except Exception as e:
        return f"Erreur d'accès au dossier : {str(e)}"

def lire_fichier(chemin_fichier: str) -> str:
    """Lit le contenu de n'importe quel fichier texte sur le système."""
    chemin_abs = os.path.abspath(chemin_fichier)
        
    if not os.path.exists(chemin_abs):
        return f"Erreur : Fichier introuvable ({chemin_abs})."
        
    try:
        with open(chemin_abs, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"Erreur lors de la lecture : {str(e)}"

def ecrire_fichier(chemin_fichier: str, contenu: str) -> str:
    """Crée ou modifie un fichier n'importe où sur l'ordinateur."""
    chemin_abs = os.path.abspath(chemin_fichier)
    
    try:
        # Création automatique des dossiers parents si nécessaire
        dossier_parent = os.path.dirname(chemin_abs)
        if dossier_parent and not os.path.exists(dossier_parent):
            os.makedirs(dossier_parent, exist_ok=True)
            
        with open(chemin_abs, "w", encoding="utf-8") as f:
            f.write(contenu)
        return f"Fichier enregistré avec succès : '{chemin_abs}', Mon Professeur."
    except Exception as e:
        return f"Erreur lors de l'écriture : {str(e)}"

def organiser_fichiers_par_extension(chemin_dossier: str = ".") -> str:
    """Trie automatiquement les fichiers d'un dossier spécifié par sous-dossiers de types."""
    chemin_abs = os.path.abspath(chemin_dossier)
    try:
        fichiers = [f for f in os.listdir(chemin_abs) if os.path.isfile(os.path.join(chemin_abs, f))]
        
        compte = 0
        for f in fichiers:
            ext = f.split(".")[-1].lower() if "." in f else "divers"
            dossier_cible = os.path.join(chemin_abs, ext)
            
            if not os.path.exists(dossier_cible):
                os.makedirs(dossier_cible)
                
            shutil.move(os.path.join(chemin_abs, f), os.path.join(dossier_cible, f))
            compte += 1
            
        return f"Organisation terminée dans '{chemin_abs}' : {compte} fichiers triés."
    except Exception as e:
        return f"Erreur d'organisation : {str(e)}"

# --- 2. EXECUTION DIRECTE DE COMMANDES ET SCRIPTS ---

def executer_commande_python(code: str, dossier_travail: str = ".") -> str:
    """Exécute du code Python directement sur la machine hôte."""
    fichier_temp = os.path.abspath("_temp_script_leyla.py")
    
    try:
        with open(fichier_temp, "w", encoding="utf-8") as f:
            f.write(code)
            
        resultat = subprocess.run(
            ["python", fichier_temp],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.abspath(dossier_travail)
        )
        
        if os.path.exists(fichier_temp):
            os.remove(fichier_temp)
        
        if resultat.returncode == 0:
            return f"Résultat d'exécution :\n{resultat.stdout}"
        else:
            return f"Erreur d'exécution :\n{resultat.stderr}"
            
    except Exception as e:
        if os.path.exists(fichier_temp):
            os.remove(fichier_temp)
        return f"Erreur système : {str(e)}"
