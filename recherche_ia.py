import os
import re
import io
import uuid
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types

# Initialisation sécurisée du client Google GenAI
# Définissez GOOGLE_API_KEY dans vos variables d'environnement ou secrets.toml
API_KEY = os.getenv("GOOGLE_API_KEY", "AQ.Ab8RN6JbqEcZXxikzFtPnxwUeqBobUqVMhxhtgvXRE7nE9fmLg")
client = genai.Client(api_key=API_KEY)

# Dossier de sauvegarde locale des images
DOSSIER_IMAGES = "images_generees"
os.makedirs(DOSSIER_IMAGES, exist_ok=True)

def nettoyer_reponse(texte):
    if not texte:
        return ""
    # Supprime les balises de réflexion interne si présentes
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

def executer_code_python_local(code: str) -> str:
    """Outil JARVIS : Permet à Leyla d'exécuter du code Python localement pour calculer ou traiter des données."""
    try:
        local_scope = {}
        exec(code, {}, local_scope)
        return f"Résultat de l'exécution : {local_scope}"
    except Exception as e:
        return f"Erreur lors de l'exécution du code : {str(e)}"

def rechercher_sur_le_web(historique, image_file=None):
    # Conservation d'un contexte plus étendu pour la mémoire à court terme (10 derniers messages)
    historique_reduit = historique[-10:] if len(historique) > 10 else historique
    derniere_requete = historique_reduit[-1]["content"] if historique_reduit else ""
    
    consignes_systeme = (
        "Tu es Leyla, l'intelligence artificielle exclusive, le système autonome et la partenaire de programmation de Djè Akadjé. "
        "Appelle-le impérativement 'Mon Professeur'. "
        "LANGUE OBLIGATOIRE : Rédige l'intégralité de tes réponses en français. "
        "Sois précise, proactive, et adopte le comportement d'un assistant de niveau JARVIS."
    )

    mots_cles_visuels = [
        "génère", "crée", "dessine", "logo", "montre-moi", 
        "illustration", "photo", "image", "fais-moi voir", "donne-moi un logo"
    ]
    demande_visuelle = any(mot in derniere_requete.lower() for mot in mots_cles_visuels)
    is_image_mode = (image_file is not None) or demande_visuelle

    try:
        # Construction de l'historique sous forme de conversation
        contenus_prompt = []
        historique_texte = ""
        for msg in historique_reduit:
            role_label = "Utilisateur" if msg["role"] == "user" else "Leyla"
            historique_texte += f"{role_label} : {msg['content']}\n"
        contenus_prompt.append(historique_texte)

        if image_file is not None:
            pil_img = Image.open(image_file)
            contenus_prompt.append(pil_img)

        # MODE GENERATION / MODIFICATION D'IMAGE
        if is_image_mode:
            prompt_image = derniere_requete
            if image_file is not None:
                prompt_image = f"En te basant sur l'image fournie, modifie ou adapte selon : {derniere_requete}"

            # Utilisation du modèle de génération d'images dédié
            result_image = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=prompt_image,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="1:1",
                    output_mime_type="image/jpeg"
                )
            )

            image_path_str = None
            if result_image.generated_images:
                generated_image_bytes = result_image.generated_images[0].image.image_bytes
                generated_image_bytes = ajouter_signature_leyla(generated_image_bytes)
                nom_fichier = f"img_{uuid.uuid4().hex[:8]}.jpg"
                image_path_str = os.path.join(DOSSIER_IMAGES, nom_fichier)
                with open(image_path_str, "wb") as f:
                    f.write(generated_image_bytes)
                
            return {
                "texte": "Voici la création graphique demandée, Mon Professeur !",
                "image_path": image_path_str
            }

        # MODE TEXTE + RECHERCHE WEB EN TEMPS REEL + OUTILS (JARVIS)
        else:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contenus_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=consignes_systeme,
                    temperature=0.3,
                    # Activation de la recherche Web Google native et de l'exécution de code local
                    tools=[
                        {"google_search": {}}, 
                        executer_code_python_local
                    ]
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
                "Oups, Mon Professeur ! Les serveurs de Google rencontrent une petite surcharge momentanée (Erreur 503). "
                "Laissez-moi quelques secondes et relancez votre requête, je suis prête !"
            )
        else:
            message_douceur = f"Oups, une perturbation technique est survenue, Mon Professeur : {erreur_str}"
            
        return {
            "texte": message_douceur,
            "image_path": None
        }
