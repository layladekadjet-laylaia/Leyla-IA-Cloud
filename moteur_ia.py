import streamlit as st
import uuid
import os
import re
import base64
import streamlit.components.v1 as components
import db_manager
from recherche_ia import rechercher_sur_le_web

# --- INITIALISATION ---
db_manager.init_db()
st.set_page_config(page_title="Leyla IA", page_icon="🤖", layout="centered")

# --- FONCTION LOGO ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

img_base64 = get_base64_image("LOGO LAYLA.png")

# --- CSS ---
st.markdown(f"""
<style>
    .stApp {{ background-color: #ffffff; }}
    .stApp::before {{ content: ""; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 300px; height: 300px; background-image: url("data:image/png;base64,{img_base64}"); background-repeat: no-repeat; opacity: 0.2; pointer-events: none; z-index: 0; }}
</style>
""", unsafe_allow_html=True)

# --- SESSION ---
user_name = db_manager.get_user_name()
if not user_name:
    st.title("🤖 Bienvenue")
    nom_saisi = st.text_input("Comment dois-je vous appeler ?")
    if nom_saisi:
        db_manager.save_user_name(nom_saisi)
        st.rerun()
    st.stop()

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

# --- SIDEBAR ---
with st.sidebar:
    if st.button("➕ Nouvelle Discussion"): 
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.rerun()
    activer_voix = st.checkbox("Réponse vocale", value=True)
    
    # Options multimédia
    st.markdown("---")
    choix_source = st.radio("Source image :", ["Aucune", "📁 Fichier", "📷 Caméra"], horizontal=True)
    image_file = None
    if choix_source == "📁 Fichier": 
        image_file = st.file_uploader("Image", type=["jpg", "png"])
    elif choix_source == "📷 Caméra": 
        image_file = st.camera_input("Prendre une photo")

# --- AFFICHAGE HISTORIQUE ---
messages = db_manager.get_history(st.session_state.session_id)
for m in messages:
    if m["role"] != "system":
        with st.chat_message(m["role"]): 
            st.write(m["content"])

# Récupération sécurisée du dernier message de l'assistant pour les scripts vocaux
msgs_hist = db_manager.get_history(st.session_state.session_id)
derniere_reponse = next((m["content"] for m in reversed(msgs_hist) if m["role"] == "assistant"), "")
derniere_reponse_clean = re.sub(r'[\n\r]+', ' ', derniere_reponse).replace('"', '\\"')

# --- BARRE DE CONTRÔLE UNIQUE (MICRO, PLAY, PAUSE ALIGNÉS) ---
toolbar_html = f"""
<div style="display: flex; justify-content: center; gap: 15px; align-items: center; margin: 10px 0 20px 0;">
    <!-- Bouton Micro -->
    <button onclick="startListening()" style="background-color: #ff4b4b; color: white; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-size: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">🎤</button>
    
    <!-- Bouton Play -->
    <button onclick="playSpeech()" style="background-color: #f0f2f6; color: #31333F; border: 1px solid #d6d6d6; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-size: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">▶️</button>
    
    <!-- Bouton Pause -->
    <button onclick="pauseSpeech()" style="background-color: #f0f2f6; color: #31333F; border: 1px solid #d6d6d6; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-size: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">⏸️</button>
</div>

<script>
function startListening() {{
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {{
        alert("Non supporté par ce navigateur.");
        return;
    }}
    const recognition = new SpeechRecognition();
    recognition.lang = 'fr-FR';
    recognition.interimResults = false;
    recognition.onresult = function(event) {{
        const speechToText = event.results[0][0].transcript;
        const inputField = window.parent.document.querySelector('input[type="text"]');
        if (inputField) {{
            inputField.value = speechToText;
            inputField.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
    }};
    recognition.start();
}}

function playSpeech() {{
    const text = "{derniere_reponse_clean}";
    if (!text) return;
    window.parent.window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.lang = 'fr-FR';
    window.parent.window.speechSynthesis.speak(u);
}}

function pauseSpeech() {{
    window.parent.window.speechSynthesis.cancel();
}}
</script>
"""
components.html(toolbar_html, height=70)

# --- ZONE SAISIE ---
prompt = st.chat_input("Que voulez-vous savoir ?")
if prompt:
    with st.chat_message("user"):
        if image_file: 
            st.image(image_file, width=200)
        st.write(prompt)
    
    db_manager.save_message(st.session_state.session_id, "user", prompt)
    with st.chat_message("assistant"):
        reponse = rechercher_sur_le_web(db_manager.get_history(st.session_state.session_id), image_file=image_file)
        st.write(reponse)
        db_manager.save_message(st.session_state.session_id, "assistant", reponse)
        if activer_voix:
            t = re.sub(r'[\n\r]+', ' ', reponse).replace('"', '\\"')
            components.html(f"""
                <script>
                    window.parent.window.speechSynthesis.cancel();
                    var u = new SpeechSynthesisUtterance('{t}');
                    u.lang = 'fr-FR';
                    window.parent.window.speechSynthesis.speak(u);
                </script>
            """, height=0)
    st.rerun()
