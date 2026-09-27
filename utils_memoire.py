import json
import os
from google import genai
from google.genai import types
import streamlit as st

FICHIER_MEMOIRE = "memoire_long_terme.json"


def initialiser_client():
    """Initialise le client Google GenAI de manière sécurisée"""
    api_key = (
        st.secrets.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )
    return genai.Client(api_key=api_key) if api_key else None


# --- GESTION DE LA MÉMOIRE PERMANENTE (RAG LOCAL) ---


def charger_memoire_long_terme() -> dict:
    """Charge les faits et préférences enregistrés au fil du temps."""
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
    }


def sauvegarder_memoire_long_terme(data: dict):
    """Sauvegarde les faits enregistrés dans un fichier JSON local."""
    try:
        with open(FICHIER_MEMOIRE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la mémoire : {e}")


def extraire_et_sauvegarder_faits(messages: list):
    """
    Analyse la discussion récente et extrait les nouvelles informations importantes
    à retenir pour toujours (style JARVIS).
    """
    client = initialiser_client()
    if not client or not messages:
        return

    texte_discussion = ""
    for m in messages[-6:]:
        role = "Utilisateur" if m["role"] == "user" else "Leyla"
        texte_discussion += f"{role} : {m['content']}\n"

    prompt = (
        "Tu es le module de mémoire à long terme de Leyla. "
        "Analyse la conversation suivante entre 'Mon Professeur' (Djè Akadjé) et Leyla. "
        "Identifie s'il y a de nouvelles informations clés sur ses projets, ses préférences, ou des faits importants à retenir. "
        "Réponds uniquement au format JSON valide avec les clés 'nouveaux_projets', 'nouvelles_preferences', 'nouveaux_faits'. "
        "Si aucune nouvelle information importante n'est présente, renvoie des listes vides.\n\n"
        f"CONVERSATION :\n{texte_discussion}"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        if response and response.text:
            nouveaux_donnees = json.loads(response.text)
            memoire = charger_memoire_long_terme()

            # Mise à jour sans doublons
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


# --- GESTION DU RÉSUMÉ ET DU CONTEXTE ---


def generer_resume(messages: list) -> str:
    """Génère un résumé concis de la session actuelle."""
    client = initialiser_client()
    if not client or not messages:
        return "Résumé indisponible."

    texte_a_resumer = ""
    for m in messages:
        role = "Utilisateur" if m["role"] == "user" else "Leyla"
        texte_a_resumer += f"{role} : {m['content']}\n"

    prompt = (
        "Fais un résumé synthétique, factuel et structuré des points clés de cette discussion "
        f"afin de conserver le contexte pour Leyla :\n\n{texte_a_resumer}"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=300,
            ),
        )
        return (
            response.text
            if response and response.text
            else "Résumé indisponible."
        )
    except Exception as e:
        return f"Erreur lors du résumé : {str(e)}"


def charger_contexte_memoire() -> str:
    """
    Génère un bloc de texte contenant la mémoire long terme
    à injecter directement dans le prompt système de Leyla.
    """
    memoire = charger_memoire_long_terme()
    contexte = "=== MÉMOIRE À LONG TERME DE LEYLA ===\n"
    contexte += (
        f"Utilisateur principal : {memoire.get('utilisateur', 'Djè Akadjé')} "
        f"(Appellation : {memoire.get('titre', 'Mon Professeur')})\n"
    )

    if memoire.get("projets"):
        contexte += (
            f"- Projets en cours : {', '.join(memoire['projets'])}\n"
        )
    if memoire.get("preferences"):
        contexte += (
            f"- Préférences de l'utilisateur : {', '.join(memoire['preferences'])}\n"
        )
    if memoire.get("faits_cles"):
        contexte += f"- Faits importants à retenir : {'; '.join(memoire['faits_cles'])}\n"

    contexte += "=====================================\n"
    return contexte
