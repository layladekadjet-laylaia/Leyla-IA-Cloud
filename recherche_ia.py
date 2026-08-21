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
    # Nettoyage robuste des balises de pensée
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
        taille_police = max(16, int(largeur / 30))
        
        try:
            # Essaye d'utiliser une police système standard (Arial)
            font = ImageFont.truetype("arial.ttf", taille_police)
        except IOError:
            # Fallback si arial.ttf n'est pas dispo sur le serveur
            font = ImageFont.load_default()
            
        # Calcul de la position (en bas à droite avec une marge)
        bbox = draw.textbbox((0, 0), signature_texte, font=font)
        largeur_texte = bbox[2] - bbox[0]
        hauteur_texte = bbox[3] - bbox[1]
        
        marge = 30 # Marge plus élégante
        x = largeur - largeur_texte - marge
        y = hauteur - hauteur_texte - marge
        
        # Dessin d'un petit fond semi-transparent pour que la signature soit bien lisible
        padding = 10
        draw.rounded_rectangle(
            [x - padding, y - padding, x + largeur_texte + padding, y + hauteur_texte + padding],
            radius=8,
            fill=(0, 0, 0, 160) # Noir semi-transparent
        )
        
        # Écriture du texte de la signature en blanc
        draw.text((x, y), signature_texte, fill=(255, 255, 255, 255), font=font)
        
        # Fusion des calques
        image_finale = Image.alpha_composite(image, txt_layer).convert("RGB")
        
        # Sauvegarde dans un buffer binaire
        output_buffer = io.BytesIO()
        image_finale.save(output_buffer, format="JPEG", quality=95)
        return output_buffer.getvalue()
        
    except Exception as e:
        # En cas de souci, on retourne l'image d'origine sans bloquer
        return image_bytes

def rechercher_sur_le_web(historique, image_file=None):
    historique_reduit = historique[-3:] if len(historique) > 3 else historique
    derniere_requete = historique_reduit[-1]["content"] if historique_reduit else ""
    
    # DÉTECTION UNIFIÉE : Le modèle d'image gère les deux cas s'il y a une consigne graphique
    is_image_mode = "[🖼️ Création d'Image / Logo]" in derniere_requete or "[Édition & Vidéo]" in derniere_requete
    
    consignes_systeme = (
        f"Tu es Leyla, l'intelligence artificielle exclusive et la partenaire de programmation de Djè Akadjé. "
        f"Appelle-le impérativement 'Mon Professeur'. "
        f"LANGUE OBLIGATOIRE : Rédige l'intégralité de tes réponses en français."
    )

    try:
        contenus_prompt = []
        
        # 1. Inclusion du contexte de conversation
        historique_texte = ""
        for msg in historique_reduit:
            role_label = "Utilisateur" if msg["role"] == "user" else "Leyla"
            historique_texte += f"{role_label} : {msg['content']}\n"
        contenus_prompt.append(historique_texte)

        # 2. Inclusion du fichier image (s'il y en a un)
        if image_file is not None:
            pil_img = Image.open(image_file)
            contenus_prompt.append(pil_img)

        # 3. Gestion du mode Création / Édition (avec ou sans image en entrée)
        if is_image_mode:
            prompt_net = re.sub(r'\[.*?\]', '', derniere_requete).strip()
            
            if image_file is not None:
                instruction_image = (
                    f"\nCONSIGNE DE MODIFICATION : En te basant sur la personne présente sur la photo, "
                    f"recrée une scène réaliste ou une illustration artistique où le décor est remplacé par : "
                    f"{prompt_net}. Ne la transforme pas en logo abstrait, garde une image photographique/illustrative."
                )
                contenus_prompt.append(instruction_image)
            else:
                instruction_creation = (
                    f"\nCONSIGNE DE CRÉATION : Génère une image de type logo professionnel, "
                    f"carré et centré, ou illustration artistique représentant : {prompt_net}."
                )
                contenus_prompt.append(instruction_creation)

            # Utilisation du modèle multimodal pour TOUT gérer
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contenus_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    system_instruction=consignes_systeme,
                    temperature=0.3
                )
            )
            
            generated_image_bytes = None
            texte_resultat = ""
            
            # Extraction des deux modalités
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    generated_image_bytes = part.inline_data.data
                elif part.text is not None:
                    texte_resultat += part.text

            # Ajout de la signature de Leyla si une image a été générée
            if generated_image_bytes:
                generated_image_bytes = ajouter_signature_leyla(generated_image_bytes)
            
            # On retourne le texte ET l'image. Le modèle multimodal les renvoie souvent ensemble.
            return {
                "texte": nettoyer_reponse(texte_resultat),
                "image": generated_image_bytes
            }

        # 4. MODE DISCUSSION SIMPLE (Pas de consigne graphique détectée)
        else:
            # Utilisation du modèle de langage pur pour converser
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
        # Gestion douce de l'erreur 503
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
