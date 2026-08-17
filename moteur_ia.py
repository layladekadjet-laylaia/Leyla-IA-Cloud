import streamlit as st
import uuid
from recherche_ia import rechercher_sur_le_web
import db_manager
from utils_memoire import generer_resume
from gtts import gTTS
import os
import re
import speech_recognition as sr

# --- INITIALISATION ---
db_manager.init_db()
st.set_page_config(page_title="Leyla IA", page_icon="🤖", layout="centered")

# --- GESTION DES SESSIONS ---
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

# --- SIDEBAR : GESTION DES SESSIONS ---
with st.sidebar:
    st.title("Mes Discussions")
    if st.button("➕ Nouvelle Discussion"):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.rerun()
    
    sessions = db_manager.get_all_sessions()
    for s in sessions:
        if st.button(f"💬 Discussion {s}", key=s):
            st.session_state.session_id = s
            st.rerun()

# --- LOGIQUE PROFIL & CSS ---
# (Gardez votre CSS ici...)

user_name = db_manager.get_user_name()
# ... (votre bloc de vérification de nom reste identique)

st.title(f"🤖 Discussion {st.session_state.session_id}")

# --- RÉCUPÉRATION HISTORIQUE ---
messages = db_manager.get_history(st.session_state.session_id)
for message in messages:
    with st.chat_message(message["role"]): 
        st.markdown(message["content"])

# --- ZONE DE SAISIE UNIFIÉE ---
# On crée des colonnes pour aligner les outils au-dessus/autour du chat_input
col1, col2, col3 = st.columns([1, 1, 6])
with col1:
    fichier = st.file_uploader("📁", type=["jpg", "png"], label_visibility="collapsed")
with col2:
    vocal = st.audio_input("🎙️")

prompt_texte = st.chat_input(f"Que voulez-vous savoir, {user_name} ?")

# --- TRAITEMENT ---
prompt = None
if vocal:
    # (Votre logique de transcription ici...)
    prompt = prompt_vocal
elif prompt_texte:
    prompt = prompt_texte

if prompt:
    # 1. Afficher l'utilisateur
    with st.chat_message("user"):
        if fichier: st.image(fichier, width=200)
        st.markdown(prompt)
    
    # 2. Sauvegarder dans la session active
    db_manager.save_message(st.session_state.session_id, "user", prompt)
    
    # 3. Réponse de Leyla
    with st.chat_message("assistant"):
        reponse = rechercher_sur_le_web(db_manager.get_history(st.session_state.session_id))
        st.markdown(reponse)
        # (Logique image et TTS ici...)
        
    db_manager.save_message(st.session_state.session_id, "assistant", reponse)
    st.rerun()
