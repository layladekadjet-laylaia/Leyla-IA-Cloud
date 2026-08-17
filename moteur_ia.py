import streamlit as st
import uuid
from recherche_ia import rechercher_sur_le_web
import db_manager
import streamlit.components.v1 as components
from utils_memoire import generer_resume
import os
import re
import speech_recognition as sr
import base64

# --- INITIALISATION ---
db_manager.init_db()
st.set_page_config(page_title="Leyla IA", page_icon="🤖", layout="centered")

# --- FONCTION DE CONVERSION DU LOGO EN BASE64 ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

img_base64 = get_base64_image("LOGO LAYLA.png")

# --- PERSONNALISATION CSS & LOGO EN ARRIÈRE-PLAN (FILIGRANE) ---
st.markdown(f"""
<style>
    .stApp {{ 
        background-color: #ffffff; 
        color: #1f1f1f; 
    }}
    .stApp::before {{
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 450px;
        height: 450px;
        background-image: url("data:image/png;base64,{img_base64}");
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
        opacity: 0.12; /* Ajustez la transparence si besoin (ex: 0.12 pour un beau filigrane discret) */
        pointer-events: none;
        z-index: 0;
    }}
    .stChatMessage {{ 
        border-radius: 16px; 
        padding: 12px 16px; 
        margin-bottom: 10px; 
        background-color: rgba(248, 249, 250, 0.95); 
        border: 1px solid #e5e5e5; 
        position: relative;
        z-index: 1;
    }}
    .stChatInputContainer input {{ 
        border-radius: 24px !important; 
        background-color: #f0f4f9 !important; 
        color: #1f1f1f !important; 
        border: 1px solid #c4c7c5 !important; 
    }}
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
    st.stop()

# --- GESTION DES SESSIONS DE DISCUSSION ---
if 'session_id' not in st.session_state:
    sessions_existantes = db_manager.get_all_sessions()
    if sessions_existantes:
        st.session_state.session_id = sessions_existantes[-1]
    else:
        st.session_state.session_id = str(uuid.uuid4())[:8]

# --- BARRE LATÉRALE : SESSIONS & PARAMÈTRES ---
with st.sidebar:
    st.header("Mes Discussions")
    if st.button("➕ Nouvelle Discussion", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.rerun()
    
    st.markdown("---")
    sessions = db_manager.get_all_sessions()
    for s in sessions:
        label_btn = f"💬 Discussion {s[:4]}..."
        if s == st.session_state.session_id:
            label_btn = f"▶️ {label_btn}"
        if st.button(label_btn, key=s, use_container_width=True):
            st.session_state.session_id = s
            st.rerun()
            
    st.markdown("---")
    st.header("Paramètres")
    activer_voix = st.checkbox("Activer la réponse vocale", value=True)
    
    if st.button("🗑️ Effacer cette discussion", use_container_width=True):
        db_manager.clear_session(st.session_state.session_id)
        st.success("Discussion effacée !")
        st.rerun()
        
    st.markdown("---")
    st.write("Développé pour Mon Professeur.")

# --- EN-TÊTE ÉPURÉ ---
st.title(f"🤖 Bonjour {user_name} !")
st.write(f"Session active : `{st.session_state.session_id}`")
st.markdown("---")

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

# Récupération de l'historique
messages = db_manager.get_history(st.session_state.session_id)

# --- GESTION DE LA MÉMOIRE LONGUE ---
if len(messages) > 10:
    dernier_msg = messages[-1]["content"] if messages else ""
    if not dernier_msg.startswith("[Résumé automatique]"):
        with st.spinner("Leyla consolide sa mémoire à long terme..."):
            resume_texte = generer_resume(messages)
            message_resume = f"[Résumé automatique] : {resume_texte}"
            db_manager.save_message(st.session_state.session_id, "system", message_resume)
            messages = db_manager.get_history(st.session_state.session_id)

# --- AFFICHAGE DE L'HISTORIQUE ---
for message in messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]): 
            st.markdown(message["content"])

# --- OPTIONS MULTIMÉDIA (SÉPARÉES) ---
with st.expander("📁 Options d'envoi d'image", expanded=False):
    choix_source = st.radio("Source de l'image :", ["Aucune", "📁 Importer un fichier", "📷 Caméra"], horizontal=True)
    image_finale = None
    if choix_source == "📁 Importer un fichier":
        image_finale = st.file_uploader("Choisissez une image", type=["jpg", "jpeg", "png"])
    elif choix_source == "📷 Caméra":
        image_finale = st.camera_input("Prenez une photo")

# --- ZONE BASSE : TOUS LES CONTRÔLES RASSEMBLÉS EN LIGNE ---

# 1. Enregistrement vocal discret
audio_file = st.audio_input("🎙️ Enregistrer un message vocal")

prompt_vocal = None
if audio_file:
    if 'last_audio_id' not in st.session_state:
        st.session_state.last_audio_id = None

    audio_bytes = audio_file.getvalue()
    if audio_bytes != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio_bytes
        
        with open("temp_audio.wav", "wb") as f: 
            f.write(audio_bytes)
        try:
            r = sr.Recognizer()
            with sr.AudioFile("temp_audio.wav") as source:
                audio_data = r.record(source)
                prompt_vocal = r.recognize_google(audio_data, language="fr-FR")
        except Exception: 
            st.warning("Impossible de transcrire l'audio.")
        finally:
            if os.path.exists("temp_audio.wav"):
                os.remove("temp_audio.wav")
        image_finale = None

# 2. Boutons Écouter, Stop et un espace alignés côte à côte juste au-dessus de la saisie
col_play, col_stop, col_espace = st.columns([1, 1, 1])

with col_play:
    if st.button("▶️ Écouter", use_container_width=True, key="btn_ecouter_bas"):
        messages_actuels = db_manager.get_history(st.session_state.session_id)
        derniere_reponse = ""
        for m in reversed(messages_actuels):
            if m["role"] == "assistant":
                derniere_reponse = m["content"]
                break
        if derniere_reponse:
            texte_propre = re.sub(r'[\n\r]+', ' ', derniere_reponse).replace('"', '\\"').replace("'", "\\'")
            components.html(
                f"""
                <script>
                    if ('speechSynthesis' in window) {{
                        window.speechSynthesis.cancel();
                        var utterance = new SpeechSynthesisUtterance("{texte_propre}");
                        utterance.lang = 'fr-FR';
                        utterance.rate = 1.0;
                        window.speechSynthesis.speak(utterance);
                    }}
                </script>
                """,
                height=0,
            )

with col_stop:
    if st.button("⏹️ Stop", use_container_width=True, key="btn_stop_bas"):
        components.html("<script>window.speechSynthesis.cancel();</script>", height=0)

# 3. Zone de saisie manuelle (placée par Streamlit tout en bas)
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

    db_manager.save_message(st.session_state.session_id, "user", contenu_u)
    messages_actuels = db_manager.get_history(st.session_state.session_id)

    with st.chat_message("assistant"):
        with st.spinner("Leyla réfléchit et analyse..."):
            reponse = rechercher_sur_le_web(messages_actuels)
            st.markdown(reponse)

            img_url = get_image_for_text(reponse)
            if img_url: 
                st.image(img_url, width=400, caption="Illustration automatique")

            if activer_voix:
                texte_propre = re.sub(r'[\n\r]+', ' ', reponse).replace('"', '\\"').replace("'", "\\'")
                components.html(
                    f"""
                    <script>
                        if ('speechSynthesis' in window) {{
                            window.speechSynthesis.cancel();
                            var utterance = new SpeechSynthesisUtterance("{texte_propre}");
                            utterance.lang = 'fr-FR';
                            utterance.rate = 1.0;
                            window.speechSynthesis.speak(utterance);
                        }}
                    </script>
                    """,
                    height=0,
                )

    db_manager.save_message(st.session_state.session_id, "assistant", reponse)
    st.rerun()
