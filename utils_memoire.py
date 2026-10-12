import json
import os
from datetime import datetime
from google import genai
from google.genai import types
import streamlit as st

FICHIER_MEMOIRE = "memoire_long_terme.json"
MODELE_GEMINI = "gemini-3.8-flash"  # Modèle officiel Gemini 3.8 Flash


def initialiser_client():
    """Initialise le client Google GenAI de manière sécurisée."""
    api_key = (
        st.secrets.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )
    return genai.Client(api_key=api_key) if api_key else None


def charger_memoire_long_terme() -> dict:
    """Charge les faits, préférences et l'historique quotidien."""
    if os.path.exists(FICHIER_MEMOIRE):
        try:
            with open(FICHIER_MEMOIRE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "utilisateur": "Djè Akadjé",
        "titre": "Mon Professeur",
        "projets": [],
        "preferences": [],
        "faits_cles": [],
        "journal_quotidien": {}  # Stocke les résumés par date ("YYYY-MM-DD")
    }


def sauvegarder_memoire_long_terme(data: dict):
    """Sauvegarde la mémoire dans le fichier JSON local."""
    try:
        with open(FICHIER_MEMOIRE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la mémoire : {e}")


def sauvegarder_resume_journee(messages: list):
    """
    Génère un résumé complet de la session et l'enregistre dans le journal quotidien 
    sous la date du jour via Gemini 3.8 Flash.
    """
    client = initialiser_client()
    if not client or not messages:
        return

    date_aujourdhui = datetime.now().strftime("%Y-%m-%d")
    texte_session = "\n".join([f"{'Utilisateur' if m['role']=='user' else 'Leyla'} : {m['content']}" for m in messages])

    prompt = (
        f"Fais une synthèse très concise (3 à 5 puces max) des actions réalisées et décisions prises aujourd'hui ({date_aujourdhui}) "
        f"pendant cette session de travail avec Mon Professeur :\n\n{texte_session}"
    )

    try:
        response = client.models.generate_content(
            model=MODELE_GEMINI,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=300),
        )
        if response and response.text:
            memoire = charger_memoire_long_terme()
            if "journal_quotidien" not in memoire:
                memoire["journal_quotidien"] = {}
            
            # Enregistre le résumé sous la date du jour
            memoire["journal_quotidien"][date_aujourdhui] = response.text.strip()
            sauvegarder_memoire_long_terme(memoire)
            print(f"✅ Résumé du jour ({date_aujourdhui}) enregistré par Leyla !")
    except Exception as e:
        print(f"Erreur sauvegarde résumé journée : {e}")


def extraire_et_sauvegarder_faits(messages: list):
    """Analyse la discussion et extrait les faits clés ainsi que les projets."""
    client = initialiser_client()
    if not client or not messages:
        return

    texte_discussion = "\n".join([f"{'Utilisateur' if m['role']=='user' else 'Leyla'} : {m['content']}" for m in messages[-10:]])

    prompt = (
        "Tu es le module de mémoire à long terme de Leyla. "
        "Analyse la conversation suivante entre 'Mon Professeur' (Djè Akadjé) et Leyla. "
        "Identifie les nouvelles informations clés sur ses projets, ses préférences, ou des faits importants à retenir. "
        "Réponds uniquement au format JSON valide avec les clés 'nouveaux_projets', 'nouvelles_preferences', 'nouveaux_faits'. "
        "Si aucune nouvelle information importante n'est présente, renvoie des listes vides.\n\n"
        f"CONVERSATION :\n{texte_discussion}"
    )

    try:
        response = client.models.generate_content(
            model=MODELE_GEMINI,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        if response and response.text:
            nouveaux_donnees = json.loads(response.text)
            memoire = charger_memoire_long_terme()

            for p in nouveaux_donnees.get("nouveaux_projets", []):
                if p not in memoire["projets"]:
                    memoire["projets"].append(p)

            for pref in nouveaux_donnees.get("nouvelles_preferences", []):
                if pref not in memoire["preferences"]:
                    memoire["preferences"].append(pref)

            for fait in nouveaux_donnees.get("nouveaux_faits", []):
                if fait not in memoire["faits_cles"]:
                    memoire["faits_cles"].append(fait)

            sauvegarder_memoire_long_terme(memoire)

    except Exception as e:
        print(f"Erreur extraction mémoire : {e}")


def charger_contexte_memoire() -> str:
    """
    Construit le contexte temporel injecté dans le briefing matinal.
    """
    memoire = charger_memoire_long_terme()
    contexte = "=== MÉMOIRE À LONG TERME ET HISTORIQUE DE LEYLA ===\n"
    contexte += f"Utilisateur principal : {memoire.get('utilisateur', 'Djè Akadjé')} (Titre : {memoire.get('titre', 'Mon Professeur')})\n"

    if memoire.get("projets"):
        contexte += f"- Projets actifs : {', '.join(memoire['projets'])}\n"
    if memoire.get("preferences"):
        contexte += f"- Préférences : {', '.join(memoire['preferences'])}\n"
    if memoire.get("faits_cles"):
        contexte += f"- Faits majeurs : {'; '.join(memoire['faits_cles'])}\n"

    # Injection du journal quotidien des derniers jours
    journal = memoire.get("journal_quotidien", {})
    if journal:
        contexte += "\n--- HISTORIQUE DES DERNIERS JOURS ---\n"
        dates_triees = sorted(journal.keys(), reverse=True)[:5]
        for date_key in dates_triees:
            contexte += f"📅 [{date_key}] :\n{journal[date_key]}\n"

    contexte += "===================================================\n"
    return contexte
