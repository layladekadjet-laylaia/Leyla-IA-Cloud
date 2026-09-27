import json
import os
import re
from typing import List, Optional
from duckduckgo_search import DDGS
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel

import utils_memoire

app = FastAPI(
    title="Serveur Passerelle Hybride Leyla IA",
    version="4.0.0",
    description="Passerelle universelle pour PC (.exe) et Mobile (.apk)",
)

# --- SÉCURITÉ NETWORK (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INITIALISATION ET SÉCURITÉ ---
API_KEY = os.getenv(
    "GOOGLE_API_KEY", "AQ.Ab8RN6JbqEcZXxikzFtPnxwUeqBobUqVMhxhtgvXRE7nE9fmLg"
)
client = genai.Client(api_key=API_KEY)


def nettoyer_pour_lecture_vocale(texte: str) -> str:
    """Nettoie le texte pour la synthèse vocale (TTS)."""
    if not texte:
        return ""
    texte = re.sub(r"<think>.*?</think>", "", texte, flags=re.DOTALL).strip()
    texte = re.sub(r"[\*\#\_\`\~]", "", texte)
    texte = re.sub(r"\[.*?\]", "", texte)
    lignes = [ligne.strip() for ligne in texte.split("\n") if ligne.strip()]
    return " ".join(lignes)


class Message(BaseModel):
    role: str
    content: str


class RequeteClient(BaseModel):
    plateforme: str  # "windows" pour le .exe ou "android" pour l' .apk
    messages: List[Message]


# --- ENDPOINTS DE CONTRÔLE ---


@app.get("/")
async def root():
    return {
        "statut": "en_ligne",
        "systeme": "Leyla IA Core (Hybride .exe / .apk)",
        "message": "Passerelle opérationnelle, Mon Professeur.",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# --- ENDPOINT PRINCIPAL MULTI-PLATEFORME ---


@app.post("/discuter")
async def discuter(donnees: RequeteClient):
    try:
        plateforme = donnees.plateforme.lower()
        historique = [
            {"role": m.role, "content": m.content} for m in donnees.messages
        ]
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

        # 2. MÉMOIRE ET CONSIGNES D'ACTION SYSTÈME
        contexte_memoire = utils_memoire.charger_contexte_memoire()

        consignes_systeme = (
            f"{contexte_memoire}\n"
            "Tu es Leyla, l'intelligence artificielle exclusive et le système central de Djè Akadjé. "
            "Appelle-le impérativement 'Mon Professeur'. "
            "LANGUE OBLIGATOIRE : Rédige l'intégralité de ta réponse en français courant. "
            f"ENVIRONNEMENT ACTUEL : Tu communiques avec un client tournant sur la plateforme : {plateforme.upper()}.\n"
            "CAPACITÉ D'ACTION SYSTEME :\n"
            "Si l'utilisateur te demande d'effectuer une action locale sur son appareil (lire un fichier, lister un dossier, lancer une application) :\n"
            "Réponds SOUS FORME D'UN OBJET JSON STRICT au format suivant :\n"
            "{\n"
            '  "action": "NOM_DE_L_ACTION",\n'
            '  "cible": "CHEMIN_OU_PARAMETRE",\n'
            '  "message": "Explication vocale de ce que tu fais"\n'
            "}\n"
            "Sinon, réponds directement en texte brut sans formatage Markdown."
        )

        contenus_prompt = []

        if contexte_web and "indisponible" not in contexte_web:
            contenus_prompt.append(
                f"INFORMATIONS WEB EN TEMPS RÉEL :\n{contexte_web}\n"
            )

        historique_texte = "HISTORIQUE DE LA CONVERSATION :\n"
        for msg in historique_reduit:
            role_label = "Utilisateur" if msg["role"] == "user" else "Leyla"
            texte_propre_msg = re.sub(
                r"\[Image transmise\]", "", msg["content"]
            ).strip()
            historique_texte += f"{role_label} : {texte_propre_msg}\n"

        contenus_prompt.append(historique_texte)

        # 3. GÉNÉRATION GEMINI 2.5 FLASH
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contenus_prompt,
            config=types.GenerateContentConfig(
                system_instruction=consignes_systeme,
                temperature=0.2,
                max_output_tokens=1024,
                tools=[{"google_search": {}}],
            ),
        )

        texte_reponse = response.text.strip()

        # 4. DÉTECTION ET PARSING DES ORDRES D'ACTION (JSON)
        if texte_reponse.startswith("{") and texte_reponse.endswith("}"):
            try:
                ordre_json = json.loads(texte_reponse)
                return {
                    "type": "commande_systeme",
                    "plateforme": plateforme,
                    "action": ordre_json.get("action"),
                    "cible": ordre_json.get("cible"),
                    "reponse": nettoyer_pour_lecture_vocale(
                        ordre_json.get("message", "")
                    ),
                }
            except json.JSONDecodeError:
                pass

        # Réponse standard
        reponse_finale = nettoyer_pour_lecture_vocale(texte_reponse)
        return {
            "type": "message_texte",
            "plateforme": plateforme,
            "reponse": reponse_finale,
        }

    except Exception as e:
        return {
            "type": "erreur",
            "reponse": f"Une perturbation système est survenue, Mon Professeur : {str(e)}",
        }
