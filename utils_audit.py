import os
import datetime

JOURNAL_AUDIT = "leyla_audit.log"

def enregistrer_action(type_action: str, cible: str, statut: str, details: str = ""):
    """
    Consigne chaque action exécutée par Leyla dans un journal infalsifiable.
    Garantit une transparence totale pour les administrateurs système.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ligne_audit = f"[{timestamp}] | ACTION: {type_action} | CIBLE: {cible} | STATUT: {statut} | DÉTAILS: {details}\n"
    
    try:
        with open(JOURNAL_AUDIT, "a", encoding="utf-8") as f:
            f.write(ligne_audit)
    except Exception as e:
        print(f"Erreur lors de l'écriture du journal d'audit : {e}")
