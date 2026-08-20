import os
import re
from PIL import Image
from io import BytesIO
from google import genai
from google.genai import types
from duckduckgo_search import DDGS

# Initialisation du client Google GenAI
api_key = "AQ.Ab8RN6JbqEcZXxikzFtPnxwUeqBobUqVMhxhtgvXRE7nE9fmLg"
os.environ["GOOGLE_API_KEY"] = api_key
client = genai.Client(api_key=api_key)

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

def rechercher_sur_le_web(historique, image_file=None):
    historique_reduit = historique[-3:] if len(historique) > 3 else historique
    derniere_requete = historique_reduit[-1]["content"] if historique_reduit else ""
    
    # Détection automatique si l'utilisateur est en mode création d'image
    is_image_mode = "[🖼️ Création d'Image / Logo]" in derniere_requete
    
    contexte_web = ""
    if not is_image_mode:
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
    if image_file is not None:
        try:
            image_file.seek(0) if hasattr(image_file, "seek") else None
            pil_img = Image.open(image_file)
            contenus_prompt.append(pil_img)
        except Exception:
            pass

    historique_texte = ""
    for msg in historique_reduit:
        role_label = "Utilisateur" if msg["role"] == "user" else "Leyla"
        texte_propre_msg = re.sub(r'\[.*?\]', '', msg["content"]).strip()
        historique_texte += f"{role_label} : {texte_propre_msg}\n"
    contenus_prompt.append(historique_texte)

    try:
        # Si on est en mode création, on force le modèle multimodal avec sortie image
        if is_image_mode:
            response = client.models.generate_content(
                model='gemini-2.5-flash-image',
                contents=contenus_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    system_instruction=consignes_systeme,
                    image_config=types.ImageConfig(aspect_ratio="1:1"),
                    temperature=0.4,
                )
            )
            
            generated_image = None
            text_response = ""
            
            # Analyse des différentes parties de la réponse (texte + image binaire)
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.text:
                        text_response += part.text
                    elif part.inline_data:
                        image_data = part.inline_data.data
                        generated_image = Image.open(BytesIO(image_data))
            
            return {
                "texte": nettoyer_reponse(text_response) if text_response else "Voici votre création Mon Professeur.",
                "image": generated_image
            }
        
        else:
            # Mode standard (texte / recherche)
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=contenus_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=consignes_systeme,
                    temperature=0.3,
                    max_output_tokens=1024,
                )
            )
            return {
                "texte": nettoyer_reponse(response.text),
                "image": None
            }
            
    except Exception as e:
        return {
            "texte": f"Erreur IA : {str(e)}",
            "image": None
        }
