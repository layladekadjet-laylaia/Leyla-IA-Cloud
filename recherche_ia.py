import os
import re
from PIL import Image
from google import genai
from google.genai import types

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
        # MODE CRÉATION OU MODIFICATION D'IMAGE
        if is_image_mode:
            prompt_net = re.sub(r'\[.*?\]', '', derniere_requete).strip()
            
            # Préparation du contenu (texte + éventuelle image fournie)
            contenus_prompt = []
            if image_file is not None:
                pil_img = Image.open(image_file)
                contenus_prompt.append(pil_img)
                contenus_prompt.append(f"Modifie cette image selon la consigne suivante en conservant le sujet principal : {prompt_net}")
            else:
                contenus_prompt.append(f"Génère une image de type logo professionnel ou illustration artistique représentant : {prompt_net}")

            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contenus_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"]
                )
            )
            
            generated_image_bytes = None
            texte_resultat = ""
            
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    generated_image_bytes = part.inline_data.data
                elif part.text is not None:
                    texte_resultat += part.text

            return {
                "texte": f"Voici le résultat pour : '{prompt_net}', Mon Professeur. {nettoyer_reponse(texte_resultat)}",
                "image": generated_image_bytes
            }
        
        # MODE STANDARD
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
