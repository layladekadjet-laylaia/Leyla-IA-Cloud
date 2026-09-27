import os
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from google import genai
from google.genai import types
from duckduckgo_search import DDGS

app = FastAPI(title="Serveur Passerelle Leyla IA")

# --- INITIALISATION ET SÉCURITÉ ---
API_KEY = os.getenv("GOOGLE_API_KEY", "AQ.Ab8RN6JbqEcZXxikzFtPnxwUeqBobUqVMhxhtgvXRE7nE9fmLg")
client = genai.Client(api_key=API_KEY)


def nettoyer_pour_lecture_vocale(texte: str) -> str:
    """Nettoie le texte pour qu'il soit lu de manière naturelle et fluide par la voix (TTS)."""
    if not texte:
        return ""

    # Supprime les réflexions internes si présentes
    texte = re.sub(r"<think>.*?</think>", "", texte, flags=re.DOTALL).strip()

    # Supprime la mise en forme Markdown (astérisques, dièses, crochets, etc.)
    texte = re.sub(r"[\*\#\_\`\~]", "", texte)
    texte = re.sub(r"\[.*?\]", "", texte)

    # Harmonise les sauts de ligne pour une diction fluide
    lignes = [ligne.strip() for ligne in texte.split("\n") if ligne.strip()]
    return " ".join(lignes)


class Message(BaseModel):
    role: str
    content: str


@app.post("/discuter")
async def discuter(messages: List[Message]):
    try:
        # Conversion et extension du contexte (10 derniers messages au lieu de 3)
        historique = [{"role": m.role, "content": m.content} for m in messages]
        historique_reduit = (
            historique[-10:] if len(historique) > 10 else historique
        )

        derniere_requete = (
            historique_reduit[-1]["content"] if historique_reduit else ""
        )

        # 1. RECHERCHE WEB DE SECOURS (DuckDuckGo)
        contexte_web = ""
        try:
            with DDGS() as ddgs:
                resultats = list(ddgs.text(derniere_requete, max_results=3))
                for item in resultats:
                    contexte_web += (
                        f"- {item.get('title', '')}: {item.get('body', '')}\n"
                    )
        except Exception:
            contexte_web = "Recherche DuckDuckGo indisponible."

        # 2. CONSIGNES SYSTÈME DÉDIÉES À LA VOIX ET AU RÔLE
        consignes_systeme = (
            "Tu es Leyla, l'intelligence artificielle exclusive et le système central de Djè Akadjé. "
            "Appelle-le impérativement 'Mon Professeur'. "
            "LANGUE OBLIGATOIRE : Rédige l'intégralité de ta réponse en français courant. "
            "RÈGLE DE VOIX : N'utilise AUCUN symbole de mise en forme Markdown (pas d'astérisques, pas de tirets, pas de dièses). "
            "Rédige uniquement du texte brut fluide, clair et adapté à une diction vocale."
        )

        contenus_prompt = []

        # INJECTION CRUCIALE : Ajout des données Web dans le prompt
        if contexte_web and "indisponible" not in contexte_web:
            contenus_prompt.append(
                f"INFORMATIONS WEB EN TEMPS RÉEL :\n{contexte_web}\n"
            )

        # Construction de l'historique textuel
        historique_texte = "HISTORIQUE DE LA CONVERSATION :\n"
        for msg in historique_reduit:
            role_label = "Utilisateur" if msg["role"] == "user" else "Leyla"
            texte_propre_msg = re.sub(
                r"\[Image transmise\]", "", msg["content"]
            ).strip()
            historique_texte += f"{role_label} : {texte_propre_msg}\n"

        contenus_prompt.append(historique_texte)

        # 3. GÉNÉRATION AVEC GEMINI 2.5 FLASH + SEARCH GROUNDING NORTATIF
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contenus_prompt,
            config=types.GenerateContentConfig(
                system_instruction=consignes_systeme,
                temperature=0.3,
                max_output_tokens=1024,
                tools=[{"google_search": {}}],  # Recherche Google native
            ),
        )

        reponse_finale = nettoyer_pour_lecture_vocale(response.text)
        return {"reponse": reponse_finale}

    except Exception as e:
        return {
            "reponse": f"Une perturbation système est survenue, Mon Professeur : {str(e)}"
        }
