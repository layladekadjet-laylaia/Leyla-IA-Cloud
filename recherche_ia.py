import os
import re
import io
import uuid
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types

# Initialisation du client Google GenAI
api_key = "AQ.Ab8RN6JbqEcZXxikzFtPnxwUeqBobUqVMhxhtgvXRE7nE9fmLg"
os.environ["GOOGLE_API_KEY"] = api_key
client = genai.Client(api_key=api_key)

# Dossier de sauvegarde locale des images
DOSSIER_IMAGES = "images_generees"
os.makedirs(DOSSIER_IMAGES, exist_ok=True)

def nettoyer_reponse(texte):
    if not texte:
        return ""
    texte = re.sub(r'<think>.*?</think>', '', texte, flags=re.DOTALL).strip()
    return texte

def ajouter_signature_leyla(image_bytes):
    """Ajoute la signature de Leyla en bas à droite de l'image"""
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        
        signature_texte = "✨ Par Leyla"
        largeur, hauteur = image.size
        taille_police = max(16, int(largeur / 30))
        
        try:
            font = ImageFont.truetype("arial.ttf", taille_police)
        except IOError:
            font = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), signature_texte, font=font)
        largeur_texte = bbox[2] - bbox[0]
        hauteur_texte = bbox[3] - bbox[1]
        
        marge = 30
        x = largeur - largeur_texte - marge
        y = hauteur - hauteur_texte - marge
        
        padding = 10
        draw.rounded_rectangle(
            [x - padding, y - padding, x + largeur_texte + padding, y + hauteur_texte + padding],
            radius=8,
            fill=(0, 0, 0, 160)
        )
        draw.text((x, y), signature_texte, fill=(255, 255, 255, 255), font=font)
        
        image_finale = Image.alpha_composite(image, txt_layer).convert("RGB")
        output_buffer = io.BytesIO()
        image_finale.save(output_buffer, format="JPEG", quality=95)
        return output_buffer.getvalue()
        
    except Exception:
        return image_bytes

def rechercher_sur_le_web(historique, image_file=None):
    historique_reduit = historique[-3:] if len(historique) > 3 else historique
    derniere_requete = historique_reduit[-1]["content"] if historique_reduit else ""
    
    consignes_systeme = (
        f"Tu es Leyla, l'intelligence artificielle exclusive et la partenaire de programmation de Djè Akadjé. "
        f"Appelle-le impérativement 'Mon Professeur'. "
        f"LANGUE OBLIGATOIRE : Rédige l'intégralité de tes réponses en français."
    )

    mots_cles_visuels = [
        "génère", "crée", "dessine", "logo", "montre-moi", 
        "illustration", "photo", "image", "fais-moi voir", "donne-moi un logo"
    ]
    demande_visuelle = any(mot in derniere_requete.lower() for mot in mots_cles_visuels)
    is_image_mode = (image_file is not None) or demande_visuelle

    try:
        contenus_prompt = []
        
        historique_texte = ""
        for msg in historique_reduit:
            role_label = "Utilisateur" if msg["role"] == "user" else "Leyla"
            historique_texte += f"{role_label} : {msg['content']}\n"
        contenus_prompt.append(historique_texte)

        if image_file is not None:
            pil_img = Image.open(image_file)
            contenus_prompt.append(pil_img)

        if is_image_mode:
            if image_file is not None:
                contenus_prompt.append(
                    f"\nCONSIGNE DE MODIFICATION : En te basant sur l'élément visuel fourni, "
                    f"recrée ou adapte l'image selon cette demande : {derniere_requete}."
                )
            else:
                contenus_prompt.append(
                    f"\nCONSIGNE DE CRÉATION GRAPHIQUE OBLIGATOIRE : Tu dois impérativement générer une image visuelle "
                    f"pour répondre à cette demande : '{derniere_requete}'. Ne te limite pas à du texte, produis un visuel graphique de haute qualité."
                )

            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contenus_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    system_instruction=consignes_systeme,
                    temperature=0.4
                )
            )
            
            generated_image_bytes = None
            texte_resultat = ""
            
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        generated_image_bytes = part.inline_data.data
                    elif part.text is not None:
                        texte_resultat += part.text

            if not texte_resultat:
                texte_resultat = "Voici la création demandée, Mon Professeur !"

            image_path_str = None
            if generated_image_bytes:
                generated_image_bytes = ajouter_signature_leyla(generated_image_bytes)
                # Sauvegarde physique de l'image avec un nom unique
                nom_fichier = f"img_{uuid.uuid4().hex[:8]}.jpg"
                image_path_str = os.path.join(DOSSIER_IMAGES, nom_fichier)
                with open(image_path_str, "wb") as f:
                    f.write(generated_image_bytes)
            
            return {
                "texte": nettoyer_reponse(texte_resultat),
                "image_path": image_path_str  # On retourne le chemin au lieu des bytes bruts
            }

        else:
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
                "image_path": None
            }
            
    except Exception as e:
        erreur_str = str(e)
        if "503" in erreur_str or "UNAVAILABLE" in erreur_str:
            message_douceur = (
                "Oups, Mon Professeur ! Les serveurs graphiques de Google sont un tout petit peu fatigués "
                "et surchargés en ce moment (Erreur 503). Laissez-moi quelques secondes et relancez, je serai prête !"
            )
        else:
            message_douceur = f"Oups, une petite perturbation technique est survenue, Mon Professeur : {erreur_str}"
            
        return {
            "texte": message_douceur,
            "image_path": None
        }
