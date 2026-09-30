import os
import re
import time
from google import genai
from google.genai import types
import utils_memoire


def obtenir_client_genai():
    """Récupère dynamiquement la clé API depuis Streamlit Secrets ou l'environnement système."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not api_key:
        try:
            import streamlit as st

            api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get(
                "GEMINI_API_KEY"
            )
        except Exception:
            pass

    if api_key:
        return genai.Client(api_key=api_key)
    return None


def nettoyer_reponse(texte: str) -> str:
    """Nettoie le texte généré pour supprimer les réflexions internes de l'IA."""
    if not texte:
        return ""
    return re.sub(r"<think>.*?</think>", "", texte, flags=re.DOTALL).strip()


def generer_briefing_matinal() -> str:
    """Génère un rapport proactif complet pour Mon Professeur (Météo, Projets, Rappels)."""
    client = obtenir_client_genai()

    if not client:
        return "Bonjour Mon Professeur. Aucune clé API Google (GOOGLE_API_KEY) n'a été détectée. Veuillez configurer votre clé dans l'environnement ou dans .streamlit/secrets.toml."

    contexte_memoire = utils_memoire.charger_contexte_memoire()

    prompt_briefing = (
        f"{contexte_memoire}\n"
        "Génère un briefing matinal proactif et élégant de niveau JARVIS pour Djè Akadjé. "
        "Appelle-le impérativement 'Mon Professeur'. "
        "Le briefing doit inclure :\n"
        "1. Salutation chaleureuse et motivationnelle.\n"
        "2. Un point rapide sur ses priorités de programmation/projets (Leyla, écosystème IA).\n"
        "3. Une question proactive pour savoir sur quoi il souhaite concentrer ses efforts aujourd'hui.\n"
        "Adopte un ton très professionnel, précis et dévoué."
    )

    tentatives = 4
    for essai in range(tentatives):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt_briefing,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    tools=[{"google_search": {}}],
                ),
            )
            return nettoyer_reponse(response.text)
        except Exception as err:
            err_str = str(err)
            # Gestion automatique de la saturation de quota avec attente progressive
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if essai < tentatives - 1:
                    time.sleep(3 * (essai + 1))  # 3s, puis 6s, puis 9s
                    continue
            if essai == tentatives - 1:
                return f"Bonjour Mon Professeur. Je suis prête à vous assister, bien que le briefing n'ait pu être généré (quota ou erreur technique) : {err}"
            
    return "Bonjour Mon Professeur. Une perturbation inattendue est survenue lors de la génération du briefing."


if __name__ == "__main__":
    print("🌅 Génération du Briefing Matinal...")
    rapport = generer_briefing_matinal()
    print("\n" + rapport)
