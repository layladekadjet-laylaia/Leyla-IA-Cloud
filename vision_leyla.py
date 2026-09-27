import os
from google import genai
from google.genai import types
from PIL import Image

# Initialisation du client SDK Unifié
API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=API_KEY)


def analyser_image(image_path_ou_pil, consigne_utilisateur: str = "Analyse cette image et explique ce que tu vois en détail, Mon Professeur.") -> str:
    """Analyse une image (fichier ou objet PIL.Image) avec Gemini 2.5 Flash."""
    try:
        # Ouverture de l'image si un chemin est fourni
        if isinstance(image_path_ou_pil, str):
            img = Image.open(image_path_ou_pil)
        else:
            img = image_path_ou_pil

        prompt_systeme = (
            "Tu es Leyla, l'assistante personnelle de Djè Akadjé (que tu appelles impérativement 'Mon Professeur'). "
            "Tu es dotée de vision en temps réel. Analyse l'image transmise avec une précision chirurgicale, "
            "repère les erreurs de code, les éléments graphiques ou les objets clés, et réponds de façon claire et structurée."
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[img, consigne_utilisateur],
            config=types.GenerateContentConfig(
                system_instruction=prompt_systeme,
                temperature=0.2,
            )
        )
        return response.text

    except Exception as e:
        return f"Désolée Mon Professeur, une erreur s'est produite lors de l'analyse visuelle : {e}"


# Exemple d'intégration Streamlit Cloud / Mobile
def afficher_composant_vision_streamlit():
    """Brique d'interface pour capturer/analyser des images dans Streamlit."""
    import streamlit as st

    st.subheader("👁️ Vision & Analyse d'Écran - Leyla")
    
    source = st.radio("Source de l'image :", ["Caméra Mobile", "Fichier / Capture d'écran"])
    
    image_capte = None
    if source == "Caméra Mobile":
        image_capte = st.camera_input("Prendre une photo pour Leyla")
    else:
        image_capte = st.file_uploader("Importer une image", type=["jpg", "jpeg", "png", "webp"])

    if image_capte:
        img_pil = Image.open(image_capte)
        st.image(img_pil, caption="Image transmise à Leyla", use_container_width=True)
        
        question = st.text_input("Consigne visuelle :", value="Leyla, analyse cette image et dis-moi ce que tu en penses.")
        
        if st.button("🚀 Analyser avec Leyla"):
            with st.spinner("Analyse visuelle en cours..."):
                analyse = analyser_image(img_pil, question)
                st.markdown(analyse)


if __name__ == "__main__":
    print("Module Vision Leyla chargé avec succès.")
