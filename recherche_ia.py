import os
import re
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
        # MODE CRÉATION : On utilise le modèle d'IA pour générer l'image
        if is_image_mode:
            prompt_net = re.sub(r'\[.*?\]', '', derniere_requete).strip()
            
            # Utilisation du modèle de génération d'image (Imagen)
            resultat_image = client.models.generate_images(
                model='imagen-3.0-fast-generate-001',
                prompt=f"Logo professionnel et créatif : {prompt_net}. Style épuré, haute qualité, fond neutre.",
                config=types.GenerateImagesConfig(number_of_images=1)
            )
            
            # Extraction de l'image générée
            generated_image = resultat_image.generated_images[0].image.image_bytes
            
            return {
                "texte": f"J'ai généré cette création visuelle pour : '{prompt_net}', Mon Professeur.",
                "image": generated_image
            }
        
        # MODE STANDARD : Texte, Code et Recherche
        else:
            # ... (votre code standard reste identique)
            contenus_prompt = []
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
