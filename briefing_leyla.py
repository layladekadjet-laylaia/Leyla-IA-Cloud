import os
from google import genai
from google.genai import types
import utils_memoire

# Initialisation du client
API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=API_KEY)


def generer_briefing_matinal() -> str:
    """Génère un rapport proactif complet pour Mon Professeur (Météo, Projets, Rappels)."""

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

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_briefing,
            config=types.GenerateContentConfig(
                temperature=0.4,
                tools=[{"google_search": {}}],  # Recherche pour actualités/infos en temps réel
            ),
        )
        return response.text
    except Exception as e:
        return f"Bonjour Mon Professeur. Je suis prête à vous assister, bien que le briefing n'ait pu être généré : {e}"


if __name__ == "__main__":
    print("🌅 Génération du Briefing Matinal...")
    rapport = generer_briefing_matinal()
    print("\n" + rapport)
