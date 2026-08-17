import streamlit as st
from recherche_ia import rechercher_sur_le_web
import db_manager
from gtts import gTTS
import os
import re
import speech_recognition as sr

# Initialisation de la base de données SQLite
db_manager.init_db()

st.set_page_config(page_title="Leyla IA", page_icon="🤖", layout="centered")

# --- PERSONNALISATION CSS STYLE CLAIR (BLANC) ---
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
        color: #1f1f1f;
    }
    .stChatMessage {
        border-radius: 16px;
        padding: 12px 16px;
        margin-bottom: 10px;
        background-color: #f8f9fa;
        border: 1px solid #e5e5e5;
    }
    .stChatInputContainer input {
        border-radius: 24px !important;
        background-color: #f0f4f9 !important;
        color: #1f1f1f !important;
        border: 1px solid #c4c7c5 !important;
    }
    h1, h2, h3, p, label {
        color: #1f1f1f !important;
    }
</style>
""", unsafe_allow_html=True)

# En-tête avec logo
try:
    st.image("LOGO LAYLA.png", width=250)
except Exception:
    pass

st.title("Leyla IA")
st.caption("Votre assistant intelligent, conçu par Djè Akadjé pour Mon Professeur.")

# Barre latérale
with st.sidebar:
    st.header("Paramètres")
    activer_voix = st.checkbox("Activer la réponse vocale", value=True)
    st.markdown("---")
    st.write("Mode Clair & Saisie Vocale actif.")

# --- DICTIONNAIRE D'IMAGES PAR MOTS-CLÉS ---
IMAGE_MAP = {
    "voiture": "https://images.unsplash.com/photo-1524985069026-b1c7d9d4f8c3?auto=format&fit=crop&w=800&q=80",
    "vélo": "https://images.unsplash.com/photo-1508609348766-92a5d6a1e7e9?auto=format&fit=crop&w=800&q=80",
    "cacao": "https://images.unsplash.com/photo-1587590227264-0ac641a9bc63?auto=format&fit=crop&w=800&q=80",
    "ordinateur": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=800&q=80",
}

def get_image_for_text(text: str) -> str | None:
    mots = re.findall(r'\b\w+\b', text.lower())
    for mot in mots:
        if mot in IMAGE_MAP:
            return IMAGE_MAP[mot]
    return None

# Récupération de l'historique
messages = db_manager.get_history()

for message in messages:
    avatar_icon = "👨‍💻" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])

# --- GESTION DE LA SAISIE VOCALE (MICROPHONE) ---
st.write("🎙️ **Parler à Leyla :**")
audio_file = st.audio_input("Enregistrez votre message vocal")

prompt_vocal = None
if audio_file is not None:
    # Sauvegarde temporaire du fichier audio enregistré
    with open("temp_audio.wav", "wb") as f:
        f.write(audio_file.getbuffer())
    
    # Transcription de l'audio en texte
    r = sr.Recognizer()
    try:
        with sr.AudioFile("temp_audio.wav") as source:
            audio_data = r.record(source)
            prompt_vocal = r.recognize_google(audio_data, language="fr-FR")
            st.success(Texte transcrit : "{prompt_vocal}")
    except Exception as e:
        st.warning("Impossible de transcrire l'audio. Veuillez réessayer ou utiliser le texte.")

# Gestion des entrées (Texte classique OU Vocal transcrit)
image_uploadee = st.file_uploader("Ajouter une image ou un fichier de diagnostic", type=["jpg", "jpeg", "png"])
prompt_texte = st.chat_input("Posez votre question à Leyla...")

# On choisit le prompt actif (priorité au vocal s'il vient d'être enregistré, sinon texte)
prompt = prompt_vocal if prompt_vocal else prompt_texte

if prompt:
    contenu_utilisateur = prompt
    if image_uploadee is not None:
        image_path = "temp_image.png"
        with open(image_path, "wb") as f:
            f.write(image_uploadee.getbuffer())
        
        with st.chat_message("user", avatar="👨‍💻"):
            st.image(image_uploadee, caption="Image transmise", width=300)
            st.markdown(prompt)
        contenu_utilisateur = f"[Image envoyée] {prompt}"
    else:
        with st.chat_message("user", avatar="👨‍💻"):
            st.markdown(prompt)

    db_manager.save_message("user", contenu_utilisateur)
    messages_actuels = db_manager.get_history()

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Leyla réfléchit..."):
            reponse = rechercher_sur_le_web(messages_actuels)
            st.markdown(reponse)
            
            # Affichage d'une image si un mot-clé correspond
            img_url = get_image_for_text(reponse)
            if img_url:
                st.image(img_url, width=400, caption="Illustration liée à la réponse")

            if activer_voix:
                try:
                    tts = gTTS(text=reponse, lang='fr', slow=False)
                    audio_path = "reponse_leyla.mp3"
                    tts.save(audio_path)
                    st.audio(audio_path, format="audio/mp3", autoplay=True)
                except Exception as e:
                    st.warning(f"Audio non disponible : {e}")
    
    db_manager.save_message("assistant", reponse)
