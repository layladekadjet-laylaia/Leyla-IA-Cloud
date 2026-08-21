import os
import re
import io
from PIL import Image, ImageDraw, ImageFont
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

def ajouter_signature_leyla(image_bytes):
    """Ajoute la signature de Leyla en bas à droite de l'image"""
    try:
        # Conversion des bytes en image PIL
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        
        # Création d'un calque pour le texte pour gérer la transparence (effet pro)
        txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        
        # Texte de la signature
        signature_texte = "✨ Par Leyla"
        
        # Taille de police adaptative selon la taille de l'image
        largeur, hauteur = image.size
        taille_police = max(12, int(largeur / 35))
        
        try:
            # Essaye d'utiliser une police système standard
            font = ImageFont.truetype("arial.ttf", taille_police)
        except IOError:
            font = ImageFont.load_default()
            
        # Calcul de la position (en bas à droite avec une marge)
        # Utilisation de textbbox pour calculer proprement la taille du texte
        bbox = draw.textbbox((0, 0), signature_texte, font=font)
        largeur_texte = bbox[2] - bbox[0]
        hauteur_texte = bbox[3] - bbox[1]
        
        marge = 20
        x = largeur - largeur_texte - marge
        y = hauteur - hauteur_texte - marge
        
        # Dessin d'un petit fond semi-transparent pour que la signature soit bien lisible
        padding = 6
        draw.rounded_rectangle(
            [x - padding, y - padding, x + largeur_texte + padding, y + hauteur_texte + padding],
            radius=5,
            fill=(0, 0, 0, 140) # Noir semi-transparent
        )
        
        # Écriture du texte de la signature en blanc
        draw.text((x, y), signature_texte, fill=(255, 255, 255, 230), font=font)
        
        # Fusion des calques
        image_finale = Image.alpha_composite(image, txt_layer).convert("RGB")
        
        # Sauvegarde dans un buffer binaire
        output_buffer = io.BytesIO()
        image_finale.save(output_buffer, format="JPEG", quality=95)
        return output_buffer.getvalue()
        
    except Exception as e:
        # En cas de petit souci, on retourne l'image d'origine sans bloquer
        return image_bytes

def rechercher_sur_le_web(historique, image_file=None):
    historique_reduit = historique[-3:] if len(historique) > 3 else historique
    derniere_requete = historique_reduit[-1]["content"] if historique_reduit else ""
    
    is_image_mode = "[🖼️ Création d'Image / Logo]" in derniere_requete or "[Édition & Vidéo]" in derniere_requete
    
    consignes_systeme = (
        f"Tu es Leyla, l'intelligence artificielle exclusive et la partenaire de programmation de Djè Akadjé. "
        f"Appelle-le impérativement 'Mon Professeur'. "
        f"LANGUE OBLIGATOIRE : Rédige l'intégralité de tes réponses en français."
    )

    try:
        if is_image_mode:
            prompt_net = re.sub(r'\[.*?\]', '', derniere_requete).strip()
            contenus_prompt = []
            
            if image_file is not None:
                pil_img = Image.open(image_file)
                contenus_prompt.append(pil_img)
                prompt_final = (
                    f"Analyse cette image et recrée une illustration artistique ou une scène réaliste inspirée par cette personne, "
                    f"en modifiant le décor ou en multipliant le sujet selon cette consigne : {prompt_net}. "
                    f"Garde un style visuel riche, soigné et expressif."
                )
                contenus_prompt.append(prompt_final)
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

            # Ajout de la signature de Leyla si une image a bien été générée
            if generated_image_bytes:
                generated_image_bytes = ajouter_signature_leyla(generated_image_bytes)

            return {
                "texte": f"Voici le résultat pour : '{prompt_net}', Mon Professeur. {nettoyer_reponse(texte_resultat)}",
                "image": generated_image_bytes
            }
        
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
        erreur_str = str(e)
        if "503" in erreur_str or "UNAVAILABLE" in erreur_str:
            message_douceur = (
                "Oups, Mon Professeur ! Les serveurs graphiques de Google sont un tout petit peu fatigués "
                "et surchargés en ce moment (Erreur 503). Laissez-moi quelques secondes de repos "
                "et relancez la création, je serai prête à nouveau !"
            )
        else:
            message_douceur = f"Oups, une petite perturbation technique est survenue, Mon Professeur : {erreur_str}"
            
        return {
            "texte": message_douceur,
            "image": None
        }
