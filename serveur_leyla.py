import os
import re
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from google import genai
from google.genai import types
from duckduckgo_search import DDGS

app = FastAPI(title="Serveur Passerelle Leyla IA")

# --- VOTRE CLE API SECRETE (Stockée uniquement sur le serveur sécurisé) ---
# Personne ne pourra la voir depuis l'application mobile (APK)
API_KEY = "AQ.Ab8RN6JbqEcZXxikzFtPnxwUeqBobUqVMhxhtgvXRE7nE9fmLg"
client = genai.Client(api_key=API_KEY)

def nettoyer_reponse(texte):
    if not texte:
        return ""
    texte = re.sub(r'<think>.*?</think>', '', texte, flags=re.DOTALL).strip()
    
    mots_anglais_interdits = [
        r'\bthe\b', r'\band\b', r'\byou\b', r'\bcan\b', r'\bimage\b', 
        r'\bvision\b', r'\bmodel\b', r'\bplease\b', r'\bnotice\b'
    ]
    for mot in mots_anglais_interdits:
        texte = re.sub(mot, '', texte, flags=re.IGNORECASE)

    lignes = texte.split('\n')
    lignes_propres = []
    derniere_ligne = ""
    for ligne in lignes:
        ligne_str = ligne.strip()
        if ligne_str and ligne_str == derniere_ligne:
            continue
        lignes_propres.append(ligne)
        if ligne_str:
            derniere_ligne = ligne_str
    return '\n'.join(lignes_propres).strip()

class Message(BaseModel):
    role: str
    content: str

@app.post("/discuter")
async def discuter(messages: List[Message]):
    # Conversion de l'historique reçu de l'APK
    historique = [{"role": m.role, "content": m.content} for m in messages]
    
    historique_reduit = historique[-3:] if len(historique) > 3 else historique
    derniere_requete = historique_reduit[-1]["content"] if historique_reduit else ""
    contexte_web = ""
    try:
        with DDGS() as ddgs:
            resultats = [r for r in ddgs.text(derniere_requete, max_results=3)]
            for item in resultats:
                contexte_web += f"- {item.get('title', '')}: {item.get('body', '')}\n"
    except Exception:
        contexte_web = "Recherche web indisponible."

    consignes_systeme = (
        f"Tu es Leyla, l'intelligence artificielle exclusive de Djè Akadjé. Appelle-le impérativement 'Mon Professeur'. "
        f"LANGUE OBLIGATOIRE : Rédige l'intégralité de ta réponse en français courant. "
        f"RÈGLE DE VOIX : N'utilise aucun symbole de mise en forme (pas d'astérisques, pas de tirets, pas de dièses). "
        f"Écris uniquement des phrases en texte brut fluide, naturel."
    )

    contenus_prompt = []
    historique_texte = ""
    for msg in historique_reduit:
        role_label = "Utilisateur" if msg["role"] == "user" else "Leyla"
        texte_propre_msg = re.sub(r'\[Image transmise\]', '', msg["content"]).strip()
        historique_texte += f"{role_label} : {texte_propre_msg}\n"
    contenus_prompt.append(historique_texte)

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Utilisation d'un modèle standard stable
            contents=contenus_prompt,
            config=types.GenerateContentConfig(
                system_instruction=consignes_systeme,
                temperature=0.3,
                max_output_tokens=1024,
            )
        )
        reponse_finale = nettoyer_reponse(response.text)
        return {"reponse": reponse_finale}
    except Exception as e:
        return {"reponse": f"Erreur IA : {str(e)}"}
