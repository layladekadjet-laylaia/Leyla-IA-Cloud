import streamlit as st
from recherche_ia import rechercher_sur_le_web
import db_manager
from utils_memoire import generer_resume
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

# En-tête avec logo
try: 
    st.image("LOGO LAYLA.png", width=300)
except Exception: 
    pass

st.title("🤖 Leyla IA")
st.write("Votre assistante personnelle intelligente, vocale, visuelle et persistante.")

# --- BARRE LATÉRALE : PROFIL & PARAMÈTRES ---
with st.sidebar:
    st.header("Profil Utilisateur")
    user_id = st.text_input("Identifiant (Nom / ID) :", value="Djè Akadjé")
    
    st.markdown("---")
    activer_voix = st.checkbox("Activer la réponse vocale", value=True)
    
    st.markdown("---")
    if st.button("🗑️ Nettoyer la mémoire"):
        db_manager.clear_history() if hasattr(db_manager, "clear_history") else None
        st.success("Mémoire effacée !")
        st.rerun()
        
    st.markdown("---")
    st.write("Développé par Mon Professeur.")

# --- DICTIONNAIRE D'IMAGES DYNAMIQUES ---
IMAGE_MAP = {
    "voiture": "https://images.unsplash.com/photo-1524985069026-b1c7d9d4f8c3?auto=format&fit=crop&w=800&q=80",
    "vélo": "https://images.unsplash.com/photo-1508609348766-92a5d6a1e7e9?auto=format&fit=crop&w=800&q=80",
    "cacao": "https://images.unsplash.com/photo-1587590227264-0ac641a9bc63?auto=format&fit=crop&w=800&q=80",
}

def get_image_for_text(text: str) -> str | None:
    mots = re.findall(r'\b\w+\b', text.lower())
    for mot in mots:
        if mot in IMAGE_MAP: 
            return IMAGE_MAP[mot]
    return None

# Récupération de l'historique spécifique à l'utilisateur
messages = db_manager.get_history_by_user(user_id) if hasattr(db_manager, "get_history_by_user") else db_manager.get_history()

# --- GESTION DE LA MÉMOIRE LONGUE (Résumé automatique si > 10 messages) ---
if len(messages) > 10:
    dernier_msg = messages[-1]["content"] if messages else ""
    if not dernier_msg.startswith("[Résumé automatique]"):
        with st.spinner("Leyla consolide sa mémoire à long terme..."):
            resume_texte = generer_resume(messages)
            message_resume = f"[Résumé automatique] : {resume_texte}"
            if hasattr(db_manager, "save_message_with_user"): # Sécurité selon la structure
                db_manager.save_message_by_user(user_id, "system", message_resume)
            else:
                db_manager.save_message("system", message_resume)
            messages = db_manager.get_history_by_user(user_id) if hasattr(db_manager, "get_history_by_user") else db_manager.get_history()

# --- AFFICHAGE DE L'HISTORIQUE ---
for message in messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]): 
            st.markdown(message["content"])

# --- BARRE D'OUTILS (Images & Vocaux) ---
col1, col2 = st.columns(2)
with col1: 
    image_uploadee = st.file_uploader("📎 Joindre une image", type=["jpg", "jpeg", "png"])
with col2: 
    audio_file = st.audio_input("🎙️ Enregistrer un vocal")

prompt_vocal = None
if audio_file:
    with open("temp_audio.wav", "wb") as f: 
        f.write(audio_file.getbuffer())
    try:
        r = sr.Recognizer()
        with sr.AudioFile("temp_audio.wav") as source:
            audio_data = r.record(source)
            prompt_vocal = r.recognize_google(audio_data, language="fr-FR")
            st.success(f"🎙️ Transcrit : {prompt_vocal}")
    except Exception: 
        st.warning("Impossible de transcrire l'audio.")

prompt_texte = st.chat_input("Que voulez-vous savoir ?")
prompt = prompt_vocal if prompt_vocal else prompt_texte

# --- TRAITEMENT DE LA REQUÊTE ---
if prompt:
    # Sauvegarde et affichage du message utilisateur
    contenu_u = prompt
    if image_uploadee is not None:
        contenu_u = f"[Image envoyée] {prompt}"

    with st.chat_message("user"):
        if image_uploadee is not None:
            st.image(image_uploadee, width=300)
        st.markdown(prompt)

    if hasattr(db_manager, "save_message_by_user"):
        db_manager.save_message_by_user(user_id, "user", contenu_u)
    else:
        db_manager.save_message("user", contenu_u)

    # Récupération actualisée pour l'IA
    messages_actuels = db_manager.get_history_by_user(user_id) if hasattr(db_manager, "get_history_by_user") else db_manager.get_history()

    # Réponse de l'assistant
    with st.chat_message("assistant"):
        with st.spinner("Leyla réfléchit..."):
            reponse = rechercher_sur_le_web(messages_actuels)
            st.markdown(reponse)

            # Affichage d'une image illustrative si détectée dans le texte
            img_url = get_image_for_text(reponse)
            if img_url: 
                st.image(img_url, width=400, caption="Illustration automatique")

            # Synthèse vocale de la réponse
            if activer_voix:
                try:
                    tts = gTTS(text=reponse, lang='fr', slow=False)
                    audio_path = "reponse_leyla.mp3"
                    tts.save(audio_path)
                    st.audio(audio_path, format="audio/mp3", autoplay=True)
                except Exception as e:
                    st.warning(f"Audio indisponible : {e}")

    # Sauvegarde de la réponse de l'assistant
    if hasattr(db_manager, "save_message_by_user"):
        db_manager.save_message_by_user(user_id, "assistant", reponse)
    else:
        db_manager.save_message("assistant", reponse)
