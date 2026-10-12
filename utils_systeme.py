import os
import shutil
import subprocess
import json
from typing import List, Dict, Optional

# --- 1. GESTION DES FICHIERS ET DOSSIERS (ACCÈS SYSTÈMES) ---

def lister_fichiers(chemin_dossier: str = ".") -> str:
    """Liste tous les fichiers et dossiers dans n'importe quel répertoire du système."""
    chemin_abs = os.path.abspath(chemin_dossier)
    
    if not os.path.exists(chemin_abs):
        return f"Erreur : Le dossier '{chemin_abs}' n'existe pas, Mon Professeur."
        
    try:
        elements = os.listdir(chemin_abs)
        fichiers = [e for e in elements if os.path.isfile(os.path.join(chemin_abs, e))]
        dossiers = [e for e in elements if os.path.isdir(os.path.join(chemin_abs, e))]
        
        return json.dumps({
            "dossier_actuel": chemin_abs,
            "dossiers": dossiers,
            "fichiers": fichiers
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Erreur d'accès au dossier : {str(e)}"

def lire_fichier(chemin_fichier: str) -> str:
    """Lit le contenu de n'importe quel fichier texte sur le système."""
    chemin_abs = os.path.abspath(chemin_fichier)
        
    if not os.path.exists(chemin_abs):
        return f"Erreur : Fichier introuvable ({chemin_abs})."
        
    # Tentative de lecture avec plusieurs encodages pour éviter les plantages (Windows/Linux)
    for encodage in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(chemin_abs, "r", encoding=encodage) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return f"Erreur lors de la lecture : {str(e)}"
            
    return "Erreur : Impossible de décoder le fichier (encodage inconnu)."

def ecrire_fichier(chemin_fichier: str, contenu: str) -> str:
    """Crée ou modifie un fichier n'importe où sur l'ordinateur de manière sécurisée."""
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
    if not os.path.exists(chemin_abs):
        return f"Erreur : Le dossier '{chemin_abs}' n'existe pas."

    try:
        fichiers = [f for f in os.listdir(chemin_abs) if os.path.isfile(os.path.join(chemin_abs, f))]
        
        compte = 0
        for f in fichiers:
            # Ignorer le script temporaire de Leyla s'il traîne
            if f == "_temp_script_leyla.py":
                continue

            ext = f.split(".")[-1].lower() if "." in f else "divers"
            dossier_cible = os.path.join(chemin_abs, ext)
            
            if not os.path.exists(dossier_cible):
                os.makedirs(dossier_cible)
                
            chemin_source = os.path.join(chemin_abs, f)
            chemin_destination = os.path.join(dossier_cible, f)
            
            # Éviter les conflits si le fichier existe déjà
            if not os.path.exists(chemin_destination):
                shutil.move(chemin_source, chemin_destination)
                compte += 1
            
        return f"Organisation terminée dans '{chemin_abs}' : {compte} fichiers triés par extension."
    except Exception as e:
        return f"Erreur d'organisation : {str(e)}"

# --- 2. EXÉCUTION CONTRÔLÉE DE SCRIPTS ---

def executer_commande_python(code: str, dossier_travail: str = ".") -> str:
    """Exécute du code Python de manière isolée et contrôlée sur la machine hôte."""
    fichier_temp = os.path.abspath("_temp_script_leyla.py")
    
    try:
        with open(fichier_temp, "w", encoding="utf-8") as f:
            f.write(code)
            
        # Utilisation de l'exécutable Python courant (sys.executable) pour garantir le bon environnement
        resultat = subprocess.run(
            [sys.executable, fichier_temp],
            capture_output=True,
            text=True,
            timeout=30,  # Sécurité anti-boucle infinie (30 secondes max)
            cwd=os.path.abspath(dossier_travail)
        )
        
        # Nettoyage systématique
        if os.path.exists(fichier_temp):
            os.remove(fichier_temp)
        
        sortie_standard = resultat.stdout.strip()
        erreur_standard = resultat.stderr.strip()

        if resultat.returncode == 0:
            return f"Exécution réussie :\n{sortie_standard if sortie_standard else '(Aucune sortie texte)'}"
        else:
            return f"Erreur lors de l'exécution du code :\n{erreur_standard}"
            
    except subprocess.TimeoutExpired:
        if os.path.exists(fichier_temp):
            os.remove(fichier_temp)
        return "⚠️ Erreur : Le script a dépassé le temps limite d'exécution (30 secondes)."
    except Exception as e:
        if os.path.exists(fichier_temp):
            os.remove(fichier_temp)
        return f"Erreur système critique : {str(e)}"
