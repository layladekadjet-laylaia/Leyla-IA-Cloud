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
    return texte

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
        # SI MODE CRÉATION : On utilise Imagen 3
        if is_image_mode:
            # On nettoie la requête pour ne garder que le sujet du logo
            prompt_net = re.sub(r'\[.*?\]', '', derniere_requete).strip()
            
            result = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=f"Un logo professionnel, moderne et élégant pour : {prompt_net}",
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="1:1"
                )
            )
            
            generated_image = None
            if result.generated_images:
                image_bytes = result.generated_images[0].image.image_bytes
                generated_image = Image.open(BytesIO(image_bytes))
            
            return {
                "texte": "Voici la création que j'ai générée pour vous Mon Professeur.",
                "image": generated_image
            }
        
        # MODE STANDARD : Texte, Code et Recherche
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
                model='gemini-2.0-flash', # Utilisation d'un modèle plus performant pour le code
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
