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

# --- PERSONNALISATION CSS ---
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #1f1f1f; }
    .stChatMessage { border-radius: 16px; padding: 12px 16px; margin-bottom: 10px; background-color: #f8f9fa; border: 1px solid #e5e5e5; }
    .stChatInputContainer input { border-radius: 24px !important; background-color: #f0f4f9 !important; color: #1f1f1f !important; border: 1px solid #c4c7c5 !important; }
</style>
""", unsafe_allow_html=True)

# En-tête
try: st.image("LOGO LAYLA.png", width=250)
except Exception: pass
st.title("Leyla IA")

# --- BARRE LATÉRALE AVEC FONCTION DE NETTOYAGE ---
with st.sidebar:
    st.header("Paramètres")
    activer_voix = st.checkbox("Activer la réponse vocale", value=True)
    st.markdown("---")
    if st.button("🗑️ Nettoyer la mémoire"):
        db_manager.clear_history()  # Assurez-vous que cette fonction existe dans db_manager.py
        st.success("Mémoire effacée !")
        st.rerun()

# --- DICTIONNAIRE D'IMAGES ---
IMAGE_MAP = {
    "voiture": "https://images.unsplash.com/photo-1524985069026-b1c7d9d4f8c3?auto=format&fit=crop&w=800&q=80",
    "vélo": "https://images.unsplash.com/photo-1508609348766-92a5d6a1e7e9?auto=format&fit=crop&w=800&q=80",
    "cacao": "https://images.unsplash.com/photo-1587590227264-0ac641a9bc63?auto=format&fit=crop&w=800&q=80",
}

def get_image_for_text(text: str) -> str | None:
    mots = re.findall(r'\b\w+\b', text.lower())
    for mot in mots:
        if mot in IMAGE_MAP: return IMAGE_MAP[mot]
    return None

# Affichage historique
messages = db_manager.get_history()
for message in messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

# --- BARRE D'OUTILS ---
col1, col2 = st.columns(2)
with col1: image_uploadee = st.file_uploader("📎 Joindre une image", type=["jpg", "jpeg", "png"])
with col2: audio_file = st.audio_input("🎙️ Enregistrer un vocal")

prompt_vocal = None
if audio_file:
    with open("temp_audio.wav", "wb") as f: f.write(audio_file.getbuffer())
    try:
        r = sr.Recognizer()
        with sr.AudioFile("temp_audio.wav") as source:
            audio_data = r.record(source)
            prompt_vocal = r.recognize_google(audio_data, language="fr-FR")
            st.success(f"🎙️ Transcrit : {prompt_vocal}")
    except: st.warning("Impossible de transcrire.")

prompt_texte = st.chat_input("Posez votre question...")
prompt = prompt_vocal if prompt_vocal else prompt_texte

if prompt:
    with st.chat_message("user"): st.markdown(prompt)
    db_manager.save_message("user", prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Leyla réfléchit..."):
            reponse = rechercher_sur_le_web(db_manager.get_history())
            st.markdown(reponse)
            
            img_url = get_image_for_text(reponse)
            if img_url: st.image(img_url, width=400)

            if activer_voix:
                try:
                    tts = gTTS(text=reponse, lang='fr', slow=False)
                    tts.save("reponse_leyla.mp3")
                    st.audio("reponse_leyla.mp3", autoplay=True)
                except: st.warning("Audio indisponible.")
    
    db_manager.save_message("assistant", reponse)
