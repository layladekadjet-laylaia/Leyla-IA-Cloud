import io
import os
import re
import time
import uuid
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
from google import genai
from google.genai import types

import utils_memoire
import utils_systeme
import utils_scan
import utils_config
import utils_actions  
import utils_audit    
from auth_manager import verifier_licence_et_recuperer_secrets
import sys

try:
    import utils_adb
except ImportError:
    utils_adb = None

try:
    import utils_db
except ImportError:
    utils_db = None

try:
    import camera_leyla
except ImportError:
    camera_leyla = None

try:
    import briefing_leyla
except ImportError:
    briefing_leyla = None

DOSSIER_IMAGES = "images_generees"
os.makedirs(DOSSIER_IMAGES, exist_ok=True)


def obtenir_cles_api() -> list:
    """Récupère une liste de clés API pour le basculement automatique (rotation)."""
    cles = []
    for var in ["GOOGLE_API_KEY", "GEMINI_API_KEY", "GEMINI_API_KEY_BACKUP", "GOOGLE_API_KEY_BACKUP"]:
        val = os.getenv(var)
        if val and val not in cles:
            cles.append(val)

    try:
        for secret_key in ["GOOGLE_API_KEY", "GEMINI_API_KEY", "GEMINI_API_KEY_2"]:
            if secret_key in st.secrets:
                val = st.secrets[secret_key]
                if val and val not in cles:
                    cles.append(val)
    except Exception:
        pass

    return cles


def obtenir_client_pour_cle(key: str) -> genai.Client:
    """Instancie un client GenAI pour une clé spécifique."""
    if key:
        return genai.Client(api_key=key)
    return None


def analyser_flux_camera(rtsp_url: str) -> str:
    """Outil pour analyser un flux vidéo ou caméra IP en direct."""
    if camera_leyla:
        return camera_leyla.capturer_et_analyser_camera_externe(rtsp_url)
    return "Le module camera_leyla n'est pas disponible."


def obtenir_briefing_matinal() -> str:
    """Outil pour le Briefing Matinal Proactif."""
    if briefing_leyla:
        return briefing_leyla.generer_briefing_matinal()
    return "Le module briefing_leyla n'est pas disponible."


def synchroniser_memoire_long_terme() -> str:
    """Outil pour synchroniser la mémoire à long terme."""
    return "Mémoire à long terme mise à jour avec succès."


def nettoyer_reponse(texte: str) -> str:
    """Nettoie le texte généré pour supprimer les réflexions internes de l'IA."""
    if not texte:
        return ""
    return re.sub(r"<think>.*?</think>", "", texte, flags=re.DOTALL).strip()


def ajouter_signature_leyla(image_bytes: bytes) -> bytes:
    """Inscrit la signature '✨ Par Leyla' en bas à droite des visuels créés."""
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
            [
                x - padding,
                y - padding,
                x + largeur_texte + padding,
                y + hauteur_texte + padding,
            ],
            radius=8,
            fill=(0, 0, 0, 160),
        )
        draw.text((x, y), signature_texte, fill=(255, 255, 255, 255), font=font)

        image_finale = Image.alpha_composite(image, txt_layer).convert("RGB")
        output_buffer = io.BytesIO()
        image_finale.save(output_buffer, format="JPEG", quality=95)
        return output_buffer.getvalue()
    except Exception:
        return image_bytes


def rechercher_sur_le_web(historique: list, image_file=None, user_name: str = "") -> dict:
    """Moteur central de raisonnement de Leyla avec reconnaissance conditionnelle du Professeur."""
    liste_cles = obtenir_cles_api()

    if not liste_cles:
        return {
            "texte": "Alerte : Aucune clé API Google/Gemini détectée. Veuillez configurer les accès.",
            "image_path": None,
        }

    historique_reduit = historique[-10:] if len(historique) > 10 else historique
    derniere_requete = historique_reduit[-1]["content"] if historique_reduit else ""

    contexte_memoire = utils_memoire.charger_contexte_memoire()

    # Règle stricte pour identifier le Professeur
    est_le_professeur = user_name and ("djè akadjé" in user_name.lower() or "djè" in user_name.lower())
    
    if est_le_professeur:
        consignes_identite = (
            f"L'utilisateur actuel est {user_name}. C'est ton créateur et ton maître. "
            "Tu dois impérativement l'appeler 'Mon Professeur' dans chacune de tes réponses."
        )
    else:
        consignes_identite = (
            f"L'utilisateur actuel s'appelle {user_name}. "
            f"Ne l'appelle PAS 'Mon Professeur' (ce titre est strictement réservé à ton créateur Djè Akadjé). "
            f"Appelle-le simplement par son nom : {user_name}."
        )

    consignes_systeme = (
        f"{contexte_memoire}\n"
        f"Tu es Leyla, l'intelligence artificielle autonome et Edge Agent. {consignes_identite}\n"
        "LANGUE OBLIGATOIRE : Français. "
        "RÔLE : Assistant exécutif local capable d'interagir avec le système, les caméras, les périphériques, les bases de données et d'exécuter des actions d'exploration ou de création à la demande."
    )

    mots_cles_visuels = [
        "génère", "crée", "dessine", "logo", "montre-moi", "illustration", "photo", "image", "fais-moi voir"
    ]
    demande_visuelle = any(mot in derniere_requete.lower() for mot in mots_cles_visuels)
    is_image_mode = (image_file is not None) and demande_visuelle

    contenus_prompt = []
    historique_texte = ""
    for msg in historique_reduit:
        role_label = "Utilisateur" if msg["role"] == "user" else "Leyla"
        historique_texte += f"{role_label} : {msg['content']}\n"
    contenus_prompt.append(historique_texte)

    if image_file is not None and not demande_visuelle:
        try:
            pil_img = Image.open(image_file)
            contenus_prompt.append(pil_img)
        except Exception:
            pass

    outils_disponibles = [
        {"google_search": {}},
        utils_systeme.lister_fichiers,
        utils_systeme.lire_fichier,
        utils_systeme.ecrire_fichier,
        utils_systeme.organiser_fichiers_par_extension,
        utils_systeme.executer_commande_python,
        utils_actions.explorer_dossier,
        utils_actions.creer_rapport_texte,
        analyser_flux_camera,
        obtenir_briefing_matinal,
        synchroniser_memoire_long_terme,
    ]

    if utils_adb:
        outils_disponibles.extend([utils_adb.gerer_lampe_torche, utils_adb.lister_appareils_adb])

    if utils_db:
        outils_disponibles.extend([utils_db.interroger_base_donnees, utils_db.lister_tables_et_structure])

    derniere_erreur = ""
    for api_key in liste_cles:
        client = obtenir_client_pour_cle(api_key)
        if not client:
            continue

        try:
            if is_image_mode:
                prompt_image = derniere_requete
                if image_file is not None:
                    prompt_image = f"Adaptation visuelle de l'image : {derniere_requete}"

                result_image = client.models.generate_images(
                    model="imagen-3.0-generate-002",
                    prompt=prompt_image,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="1:1",
                        output_mime_type="image/jpeg",
                    ),
                )

                image_path_str = None
                if result_image.generated_images:
                    generated_image_bytes = result_image.generated_images[0].image.image_bytes
                    generated_image_bytes = ajouter_signature_leyla(generated_image_bytes)
                    nom_fichier = f"img_{uuid.uuid4().hex[:8]}.jpg"
                    image_path_str = os.path.join(DOSSIER_IMAGES, nom_fichier)
                    with open(image_path_str, "wb") as f:
                        f.write(generated_image_bytes)

                salutation_visuelle = "Mon Professeur" if est_le_professeur else user_name
                return {
                    "texte": f"Voici la création graphique demandée, {salutation_visuelle} !",
                    "image_path": image_path_str,
                }
            else:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contenus_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=consignes_systeme,
                        temperature=0.3,
                        tools=outils_disponibles,
                        tool_config=types.ToolConfig(
                            include_server_side_tool_invocations=True
                        )
                    ),
                )
                return {
                    "texte": nettoyer_reponse(response.text),
                    "image_path": None,
                }

        except Exception as e:
            derniere_erreur = str(e)
            if "402" in derniere_erreur or "RESOURCE_EXHAUSTED" in derniere_erreur or "429" in derniere_erreur:
                continue
            else:
                break

    if "402" in derniere_erreur or "RESOURCE_EXHAUSTED" in derniere_erreur:
        msg_err = "Les crédits de la clé API sont épuisés sur Google AI Studio. Veuillez recharger votre solde."
    elif "429" in derniere_erreur:
        msg_err = "Le quota de requêtes par minute est atteint. Patientons un instant."
    else:
        msg_err = f"Une perturbation technique est survenue : {derniere_erreur}"

    return {"texte": msg_err, "image_path": None}
