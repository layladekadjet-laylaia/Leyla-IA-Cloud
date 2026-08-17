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

# --- GESTION DU PROFIL UTILISATEUR ---
user_name = db_manager.get_user_name()
if not user_name:
    st.title("🤖 Bienvenue sur Leyla IA")
    nom_saisi = st.text_input("Bonjour ! Je suis Leyla. Comment dois-je vous appeler ?")
    if nom_saisi:
        db_manager.save_user_name(nom_saisi)
        st.rerun()
    st.stop()  # Bloque l'interface tant que le nom n'est pas défini

# --- EN-TÊTE AVEC LOGO ET PRÉNOM ---
try: 
    st.image("LOGO LAYLA.png", width=300)
except Exception: 
    pass

st.title(f"🤖 Bonjour {user_name} !")
st.write("Votre assistante personnelle intelligente est prête.")

# --- BARRE LATÉRALE : PARAMÈTRES ---
with st.sidebar:
    st.header("Paramètres")
    activer_voix = st.checkbox("Activer la réponse vocale", value=True)
    
    st.markdown("---")
    if st.button("🗑️ Nettoyer la mémoire"):
        db_manager.clear_history()
        st.success("Mémoire effacée !")
        st.rerun()
        
    st.markdown("---")
    st.write("Développé pour Mon Professeur.")

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

# Récupération automatique de l'historique de l'appareil
messages = db_manager.get_history()

# --- GESTION DE LA MÉMOIRE LONGUE ---
if len(messages) > 10:
    dernier_msg = messages[-1]["content"] if messages else ""
    if not dernier_msg.startswith("[Résumé automatique]"):
        with st.spinner("Leyla consolide sa mémoire à long terme..."):
            resume_texte = generer_resume(messages)
            message_resume = f"[Résumé automatique] : {resume_texte}"
            db_manager.save_message("system", message_resume)
            messages = db_manager.get_history()

# --- AFFICHAGE DE L'HISTORIQUE ---
for message in messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]): 
            st.markdown(message["content"])

# --- BARRE D'OUTILS MULTIMÉDIA ---
st.markdown("### 🛠️ Options d'envoi")
choix_source = st.radio("Comment souhaitez-vous fournir une image ?", ["Aucune", "📁 Importer un fichier", "📷 Prendre une photo avec la caméra"])

image_finale = None
if choix_source == "📁 Importer un fichier":
    image_finale = st.file_uploader("Choisissez une image", type=["jpg", "jpeg", "png"])
elif choix_source == "📷 Prendre une photo avec la caméra":
    image_finale = st.camera_input("Prenez la photo de votre culture")

audio_file = st.audio_input("🎙️ Enregistrer un vocal (Optionnel)")

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

prompt_texte = st.chat_input(f"Que voulez-vous savoir, {user_name} ?")
prompt = prompt_vocal if prompt_vocal else prompt_texte

# --- TRAITEMENT DE LA REQUÊTE ---
if prompt:
    contenu_u = prompt
    if image_finale is not None:
        contenu_u = f"[Image transmise] {prompt}"

    with st.chat_message("user"):
        if image_finale is not None:
            st.image(image_finale, width=300, caption="Photo transmise à Leyla")
        st.markdown(prompt)

    db_manager.save_message("user", contenu_u)
    messages_actuels = db_manager.get_history()

    with st.chat_message("assistant"):
        with st.spinner("Leyla réfléchit et analyse..."):
            reponse = rechercher_sur_le_web(messages_actuels)
            st.markdown(reponse)

            img_url = get_image_for_text(reponse)
            if img_url: 
                st.image(img_url, width=400, caption="Illustration automatique")

            if activer_voix:
                try:
                    tts = gTTS(text=reponse, lang='fr', slow=False)
                    audio_path = "reponse_leyla.mp3"
                    tts.save(audio_path)
                    st.audio(audio_path, format="audio/mp3", autoplay=True)
                except Exception as e:
                    st.warning(f"Audio indisponible : {e}")

    db_manager.save_message("assistant", reponse)
