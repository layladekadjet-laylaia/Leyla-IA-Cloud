import os
import shutil
import subprocess
import json
from typing import List, Dict, Optional

# Dossier racine sécurisé dans lequel Leyla a le droit d'agir librement
ESPACE_TRAVAIL_SECURISE = os.path.abspath("./workspace_leyla")

def initialiser_espace_travail():
    """S'assure que le dossier de travail sécurisé existe."""
    if not os.path.exists(ESPACE_TRAVAIL_SECURISE):
        os.makedirs(ESPACE_TRAVAIL_SECURISE)

def _est_chemin_autorise(chemin: str) -> bool:
    """Vérifie que le chemin ne sort pas du dossier de travail autorisé (Anti-Path Traversal)."""
    chemin_abs = os.path.abspath(chemin)
    return chemin_abs.startswith(ESPACE_TRAVAIL_SECURISE)

# --- 1. GESTION DES FICHIERS ET DOSSIERS ---

def lister_fichiers(sous_dossier: str = "") -> str:
    """Liste tous les fichiers et dossiers dans l'espace de travail."""
    initialiser_espace_travail()
    cible = os.path.join(ESPACE_TRAVAIL_SECURISE, sous_dossier)
    
    if not _est_chemin_autorise(cible) or not os.path.exists(cible):
        return "Accès refusé ou dossier inexistant."
        
    fichiers = os.listdir(cible)
    return json.dumps(fichiers, ensure_ascii=False)

def lire_fichier(nom_fichier: str) -> str:
    """Lit le contenu d'un fichier texte dans l'espace de travail."""
    chemin = os.path.join(ESPACE_TRAVAIL_SECURISE, nom_fichier)
    
    if not _est_chemin_autorise(chemin):
        return "Erreur : Sécurité - Accès hors de l'espace de travail interdit."
        
    if not os.path.exists(chemin):
        return "Erreur : Fichier introuvable."
        
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Erreur lors de la lecture : {str(e)}"

def ecrire_fichier(nom_fichier: str, contenu: str) -> str:
    """Crée ou modifie un fichier dans l'espace de travail."""
    initialiser_espace_travail()
    chemin = os.path.join(ESPACE_TRAVAIL_SECURISE, nom_fichier)
    
    if not _est_chemin_autorise(chemin):
        return "Erreur : Sécurité - Impossible d'écrire en dehors du workspace."
        
    try:
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(contenu)
        return f"Fichier '{nom_fichier}' enregistré avec succès dans l'espace de travail."
    except Exception as e:
        return f"Erreur lors de l'écriture : {str(e)}"

def organiser_fichiers_par_extension() -> str:
    """Trie automatiquement les fichiers de l'espace de travail dans des sous-dossiers par type."""
    initialiser_espace_travail()
    try:
        fichiers = [f for f in os.listdir(ESPACE_TRAVAIL_SECURISE) if os.path.isfile(os.path.join(ESPACE_TRAVAIL_SECURISE, f))]
        
        compte = 0
        for f in fichiers:
            ext = f.split(".")[-1].lower() if "." in f else "divers"
            dossier_cible = os.path.join(ESPACE_TRAVAIL_SECURISE, ext)
            
            if not os.path.exists(dossier_cible):
                os.makedirs(dossier_cible)
                
            shutil.move(os.path.join(ESPACE_TRAVAIL_SECURISE, f), os.path.join(dossier_cible, f))
            compte += 1
            
        return f"Organisation terminée : {compte} fichiers triés par catégorie."
    except Exception as e:
        return f"Erreur d'organisation : {str(e)}"

# --- 2. EXECUTION CONTRÔLÉE DE COMMANDES ---

def executer_commande_python(code: str) -> str:
    """Exécute du code Python dans un environnement de test local."""
    initialiser_espace_travail()
    fichier_temp = os.path.join(ESPACE_TRAVAIL_SECURISE, "_temp_script.py")
    
    try:
        with open(fichier_temp, "w", encoding="utf-8") as f:
            f.write(code)
            
        resultat = subprocess.run(
            ["python", fichier_temp],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=ESPACE_TRAVAIL_SECURISE
        )
        
        os.remove(fichier_temp)
        
        if resultat.returncode == 0:
            return f"Résultat d'exécution :\n{resultat.stdout}"
        else:
            return f"Erreur d'exécution :\n{resultat.stderr}"
            
    except subprocess.TimeoutExpired:
        if os.path.exists(fichier_temp):
            os.remove(fichier_temp)
        return "Erreur : Le temps d'exécution a dépassé la limite de 10 secondes."
    except Exception as e:
        return f"Erreur système : {str(e)}"
