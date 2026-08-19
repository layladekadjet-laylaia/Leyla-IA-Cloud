import streamlit as st
import uuid
import os
import re
import base64
import speech_recognition as sr
import streamlit.components.v1 as components
import db_manager
from recherche_ia import rechercher_sur_le_web
from utils_memoire import generer_resume

# --- INITIALISATION ---
db_manager.init_db()
st.set_page_config(page_title="Leyla IA", page_icon="🤖", layout="centered")

# --- FONCTION DE CONVERSION DU LOGO ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

img_base64 = get_base64_image("LOGO LAYLA.png")

# --- CSS ---
st.markdown(f"""
<style>
    .stApp {{ background-color: #ffffff; color: #1f1f1f; }}
    .stApp::before {{
        content: ""; position: fixed; top: 50%; left: 50%;
        transform: translate(-50%, -50%); width: 450px; height: 450px;
        background-image: url("data:image/png;base64,{img_base64}");
        background-repeat: no-repeat; background-position: center;
        background-size: contain; opacity: 0.60; pointer-events: none; z-index: 0;
    }}
    .stChatMessage {{ border-radius: 16px; padding: 12px 16px; margin-bottom: 10px; background-color: rgba(248, 249, 250, 0.95); border: 1px solid #e5e5e5; position: relative; z-index: 1; }}
</style>
""", unsafe_allow_html=True)

# --- GESTION PROFIL & SESSION ---
user_name = db_manager.get_user_name()
if not user_name:
    st.title("🤖 Bienvenue sur Leyla IA")
    nom_saisi = st.text_input("Bonjour ! Je suis Leyla. Comment dois-je vous appeler ?")
    if nom_saisi:
        db_manager.save_user_name(nom_saisi)
        st.rerun()
    st.stop()

if 'session_id' not in st.session_state:
    sessions = db_manager.get_all_sessions()
    st.session_state.session_id = sessions[-1] if sessions else str(uuid.uuid4())[:8]

# --- SIDEBAR ---
with st.sidebar:
    st.header("Mes Discussions")
    if st.button("➕ Nouvelle Discussion"):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.rerun()
    activer_voix = st.checkbox("Activer la réponse vocale", value=True)
    if st.button("🗑️ Effacer cette discussion"):
        db_manager.clear_session(st.session_state.session_id)
        st.rerun()

st.title(f"🤖 Bonjour {user_name} !")

# --- LOGIQUE IA ---
messages = db_manager.get_history(st.session_state.session_id)

if len(messages) > 10:
    dernier_msg = messages[-1]["content"]
    if not dernier_msg.startswith("[Résumé automatique]"):
        with st.spinner("Leyla consolide sa mémoire..."):
            resume = generer_resume(messages)
            db_manager.save_message(st.session_state.session_id, "system", f"[Résumé automatique] : {resume}")
            messages = db_manager.get_history(st.session_state.session_id)

for message in messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.write(message["content"])

# --- SAISIE ---
prompt_texte = st.chat_input(f"Que voulez-vous savoir, {user_name} ?")
if prompt_texte:
    db_manager.save_message(st.session_state.session_id, "user", prompt_texte)
    
    with st.chat_message("assistant"):
        with st.spinner("Leyla réfléchit..."):
            reponse = rechercher_sur_le_web(db_manager.get_history(st.session_state.session_id))
            st.write(reponse)
            db_manager.save_message(st.session_state.session_id, "assistant", reponse)
            
            if activer_voix:
                texte_vocal = re.sub(r'[\n\r]+', ' ', reponse).replace('"', '\\"').replace("'", "\\'")
                components.html(f"""<script>window.speechSynthesis.speak(new SpeechSynthesisUtterance("{texte_vocal}"));</script>""", height=0)
    st.rerun()
