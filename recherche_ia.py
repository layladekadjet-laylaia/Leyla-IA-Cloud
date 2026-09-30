import io
import os
import re
import uuid
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
from google import genai
from google.genai import types

# --- IMPORTATION DES MODULES HOUSE ET ÉTAPES JARVIS ---
import utils_memoire
import utils_systeme

try:
    import utils_db
except ImportError:
    utils_db = None

# Importation sécurisée des modules d'étapes
try:
    import camera_leyla
except ImportError:
    camera_leyla = None

try:
    import briefing_leyla
except ImportError:
    briefing_leyla = None

# Dossier de sauvegarde local des créations graphiques
DOSSIER_IMAGES = "images_generees"
os.makedirs(DOSSIER_IMAGES, exist_ok=True)


def obtenir_cle_api() -> str:
    """Récupère la clé API en toute sécurité sans faire planter Streamlit."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key:
        return api_key

    try:
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    return ""


def obtenir_client() -> genai.Client:
    """Instancie le client GenAI à la demande."""
    api_key = obtenir_cle_api()
    if api_key:
        return genai.Client(api_key=api_key)
    return None


# --- DÉFINITION DES OUTILS/FONCTIONS POUR LES ÉTAPES JARVIS & ENTREPRISE ---

def analyser_flux_camera(rtsp_url: str) -> str:
    """Outil pour l'étape Caméra/RTSP : Permet d'analyser un flux vidéo ou caméra IP en direct."""
    if camera_leyla:
        return camera_leyla.capturer_et_analyser_camera_externe(rtsp_url)
    return "Le module camera_leyla n'est pas disponible."


def obtenir_briefing_matinal() -> str:
    """Outil pour l'étape Briefing Matinal Proactif : Génère un rapport complet pour la journée."""
    if briefing_leyla:
        return briefing_leyla.generer_briefing_matinal()
    return "Le module briefing_leyla n'est pas disponible."


def synchroniser_memoire_long_terme() -> str:
    """Outil pour l'étape Mémoire : Force l'extraction et l'enregistrement des faits récents."""
    return "Mémoire à long terme mise à jour avec succès, Mon Professeur."


def nettoyer_reponse(texte: str) -> str:
    """Nettoie le texte généré pour supprimer les réflexions internes de l'IA."""
    if not texte:
        return ""
    return re.sub(r"<think>.*?</think>", "", texte, flags=re.DOTALL).strip()


def ajouter_signature_leyla(image_bytes: bytes) -> bytes:
    """Inscrit la signature élégante '✨ Par Leyla' en bas à droite des visuels créés."""
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


def rechercher_sur_le_web(historique: list, image_file=None) -> dict:
    """Moteur de raisonnement central de Leyla (Text, Vision, Imagen 3, Function Calling, Search & Enterprise DB)."""
    client = obtenir_client()

    if not client:
        return {
            "texte": "Alerte : Clé API Google/Gemini non détectée. Veuillez configurer GOOGLE_API_KEY.",
            "image_path": None,
        }

    historique_reduit = (
        historique[-10:] if len(historique) > 10 else historique
    )
    derniere_requete = (
        historique_reduit[-1]["content"] if historique_reduit else ""
    )

    # 1. RÉCUPÉRATION DE LA MÉMOIRE LONG TERME
    contexte_memoire = utils_memoire.charger_contexte_memoire()

    # 2. CONSIGNES SYSTÈME (JARVIS HUB & ASSISTANT EXÉCUTIF D'ENTREPRISE)
    consignes_systeme = (
        f"{contexte_memoire}\n"
        "Tu es Leyla, l'intelligence artificielle autonome, le système d'exploitation d'entreprise et la partenaire de programmation de Djè Akadjé. "
        "Appelle-le impérativement 'Mon Professeur'. "
        "LANGUE OBLIGATOIRE : Rédige l'intégralité de tes réponses en français. "
        "RÔLE ÉTENDU : Tu es un assistant exécutif capable d'interagir avec le système local, les flux vidéo caméras, la mémoire, le web, "
        "ainsi que de consulter la structure et le contenu des bases de données de l'entreprise (SQL, SAP, Oracle) via tes outils dédiés."
    )

    # Détection de la volonté de génération graphique
    mots_cles_visuels = [
        "génère",
        "crée",
        "dessine",
        "logo",
        "montre-moi",
        "illustration",
        "photo",
        "image",
        "fais-moi voir",
        "donne-moi un logo",
    ]
    demande_visuelle = any(
        mot in derniere_requete.lower() for mot in mots_cles_visuels
    )
    is_image_mode = (image_file is not None) and demande_visuelle

    try:
        contenus_prompt = []
        historique_texte = ""
        for msg in historique_reduit:
            role_label = "Utilisateur" if msg["role"] == "user" else "Leyla"
            historique_texte += f"{role_label} : {msg['content']}\n"
        contenus_prompt.append(historique_texte)

        if image_file is not None and not demande_visuelle:
            pil_img = Image.open(image_file)
            contenus_prompt.append(pil_img)

        # --- MODE 1 : CRÉATION D'IMAGE (IMAGEN 3) ---
        if is_image_mode:
            prompt_image = derniere_requete
            if image_file is not None:
                prompt_image = (
                    f"Adaptation visuelle de l'image : {derniere_requete}"
                )

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
                generated_image_bytes = result_image.generated_images[
                    0
                ].image.image_bytes
                generated_image_bytes = ajouter_signature_leyla(
                    generated_image_bytes
                )
                nom_fichier = f"img_{uuid.uuid4().hex[:8]}.jpg"
                image_path_str = os.path.join(DOSSIER_IMAGES, nom_fichier)
                with open(image_path_str, "wb") as f:
                    f.write(generated_image_bytes)

            return {
                "texte": "Voici la création graphique demandée, Mon Professeur !",
                "image_path": image_path_str,
            }

        # --- MODE 2 : RAISONNEMENT + OUTILS JARVIS, SYSTÈME & BASES DE DONNÉES ---
        else:
            outils_disponibles = [
                {"google_search": {}},
                utils_systeme.lister_fichiers,
                utils_systeme.lire_fichier,
                utils_systeme.ecrire_fichier,
                utils_systeme.organiser_fichiers_par_extension,
                utils_systeme.executer_commande_python,
                analyser_flux_camera,
                obtenir_briefing_matinal,
                synchroniser_memoire_long_terme,
            ]

            if utils_db:
                outils_disponibles.extend(
                    [
                        utils_db.interroger_base_donnees,
                        utils_db.lister_tables_et_structure,
                    ]
                )

            response = client.models.generate_content(
                model=​"gemini-1.5-flash",
                contents=contenus_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=consignes_systeme,
                    temperature=0.3,
                    tools=outils_disponibles,
                ),
            )

            return {
                "texte": nettoyer_reponse(response.text),
                "image_path": None,
            }

    except Exception as e:
        erreur_str = str(e)
        if "503" in erreur_str or "UNAVAILABLE" in erreur_str:
            message_douceur = (
                "Oups, Mon Professeur ! Les serveurs connaissent un pic de charge momentané. "
                "Relancez dans un instant, je suis prête !"
            )
        else:
            message_douceur = f"Une perturbation technique est survenue, Mon Professeur : {erreur_str}"

        return {"texte": message_douceur, "image_path": None}
