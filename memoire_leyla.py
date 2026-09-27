import os
import json
from supabase import create_client, Client

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Initialisation du client Supabase si les clés sont présentes
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Connexion Supabase impossible : {e}")

FICHIER_MEMOIRE_LOCAL = "memoire_leyla.json"


def charger_memoire_contextuelle() -> dict:
    """Charge les préférences et la mémoire à long terme de Leyla."""
    # 1. Tentative d'extraction depuis Supabase
    if supabase:
        try:
            res = supabase.table("memoire_leyla").select("*").execute()
            if res.data:
                return {item["cle"]: item["valeur"] for item in res.data}
        except Exception as e:
            print(f"⚠️ Erreur de lecture Supabase, bascule sur le cache local : {e}")

    # 2. Fallback local (JSON sur smartphone/PC)
    if os.path.exists(FICHIER_MEMOIRE_LOCAL):
        try:
            with open(FICHIER_MEMOIRE_LOCAL, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Profil initial par défaut
    return {
        "utilisateur": "Djè Akadjé",
        "titre": "Mon Professeur",
        "projets_actifs": ["Écosystème JARVIS Leyla", "Développement Python Mobile"],
        "langages_preferes": ["Python", "SQL"],
        "style_reponse": "Professionnel, direct, courtois, hautement technique",
    }


def sauvegarder_connaissance(cle: str, valeur: str) -> bool:
    """Enregistre une nouvelle connaissance ou préférence dans la mémoire."""
    # Enregistrement local
    memoire_actuelle = charger_memoire_contextuelle()
    memoire_actuelle[cle] = valeur

    with open(FICHIER_MEMOIRE_LOCAL, "w", encoding="utf-8") as f:
        json.dump(memoire_actuelle, f, ensure_ascii=False, indent=2)

    # Synchro Supabase si disponible
    if supabase:
        try:
            supabase.table("memoire_leyla").upsert(
                {"cle": cle, "valeur": str(valeur)}
            ).execute()
            return True
        except Exception as e:
            print(f"⚠️ Échec d'envoi de la mémoire vers Supabase : {e}")

    return True


def construire_prompt_systeme_avec_memoire() -> str:
    """Génère la consigne système dynamique enrichie par la mémoire."""
    memoire = charger_memoire_contextuelle()

    prompt = (
        f"Tu es Leyla, l'IA agente avancée de {memoire.get('utilisateur', 'Djè Akadjé')}.\n"
        f"Tu dois impérativement t'adresser à lui en l'appelant '{memoire.get('titre', 'Mon Professeur')}'.\n"
        f"Style de réponse exigé : {memoire.get('style_reponse', 'Direct et très précis')}.\n\n"
        "--- CONTEXTE PERMANENT ET MÉMOIRE ---\n"
    )

    for k, v in memoire.items():
        if k not in ["utilisateur", "titre", "style_reponse"]:
            prompt += f"- {k.upper()} : {v}\n"

    prompt += "-------------------------------------\n"
    return prompt


if __name__ == "__main__":
    print("🧠 Chargement du module Mémoire Proactive...")
    prompt_complet = construire_prompt_systeme_avec_memoire()
    print("\nSystem Prompt dynamique généré par Leyla :\n")
    print(prompt_complet)
