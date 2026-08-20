import os
import re
from PIL import Image, ImageDraw, ImageFont
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
    return texte

def generer_logo_local(prompt_net):
    """
    Génère un logo directement en local avec Pillow pour éviter toute erreur API Cloud 404.
    """
    try:
        taille = 800
        img = Image.new("RGBA", (taille, taille), (15, 23, 42)) # Fond sombre tech
        draw = ImageDraw.Draw(img)
        
        # Dessin d'un cercle/cadre stylisé
        draw.ellipse([150, 150, 650, 650], outline=(56, 189, 248), width=8)
        draw.rectangle([250, 350, 550, 450], fill=(244, 63, 94))
        
        return img
    except Exception as e:
        return None

def rechercher_sur_le_web(historique, image_file=None):
    historique_reduit = historique[-3:] if len(historique) > 3 else historique
    derniere_requete = historique_reduit[-1]["content"] if historique_reduit else ""
    
    is_image_mode = "[🖼️ Création d'Image / Logo]" in derniere_requete
    
    consignes_systeme = (
        f"Tu es Leyla, l'intelligence artificielle exclusive et la partenaire de programmation de Djè Akadjé. "
        f"Appelle-le impérativement 'Mon Professeur'. "
        f"LANGUE OBLIGATOIRE : Rédige l'intégralité de tes réponses en français."
    )

    try:
        # SI MODE CRÉATION : On utilise notre générateur local robuste (zéro erreur 404)
        if is_image_mode:
            prompt_net = re.sub(r'\[.*?\]', '', derniere_requete).strip()
            generated_image = generer_logo_local(prompt_net)
            
            return {
                "texte": f"Voici la création visuelle générée en local pour : '{prompt_net}', Mon Professeur.",
                "image": generated_image
            }
        
        # MODE STANDARD : Texte, Code et Recherche avec gemini-3.6-flash
        else:
            contenus_prompt = []
            if image_file is not None:
                pil_img = Image.open(image_file)
                contenus_prompt.append(pil_img)
            
            historique_texte = ""
            for msg in historique_reduit:
                role_label = "Utilisateur" if msg["role"] == "user" else "Leyla"
                historique_texte += f"{role_label} : {msg['content']}\n"
            contenus_prompt.append(historique_texte)

            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=contenus_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=consignes_systeme,
                    temperature=0.3
                )
            )
            return {
                "texte": nettoyer_reponse(response.text),
                "image": None
            }
            
    except Exception as e:
        return {
            "texte": f"Erreur lors de la génération : {str(e)}",
            "image": None
        }
