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

if 'input_text' not in st.session_state:
    st.session_state.input_text = ""

# --- SIDEBAR ---
with st.sidebar:
    if st.button("➕ Nouvelle Discussion"): 
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.rerun()
    activer_voix = st.checkbox("Réponse vocale", value=True)
    
    st.markdown("---")
    choix_source = st.radio("Source image :", ["Aucune", "📁 Fichier", "📷 Caméra"], horizontal=True)
    image_file = None
    if choix_source == "📁 Fichier": 
        image_file = st.file_uploader("Image", type=["jpg", "png"])
    elif choix_source == "📷 Caméra": 
        image_file = st.camera_input("Prendre une photo")

# --- HISTORIQUE ---
messages = db_manager.get_history(st.session_state.session_id)
for m in messages:
    if m["role"] != "system":
        with st.chat_message(m["role"]): 
            st.write(m["content"])

derniere_reponse = next((m["content"] for m in reversed(messages) if m["role"] == "assistant"), "")
derniere_reponse_clean = re.sub(r'[\n\r]+', ' ', derniere_reponse).replace('"', '\\"')

# --- BARRE AUDIO LECTURE ---
audio_html = f"""
<div style="display: flex; justify-content: center; gap: 15px; align-items: center; margin-bottom: 10px;">
    <button onclick="playSpeech()" style="background-color: #f0f2f6; border: 1px solid #d6d6d6; padding: 6px 14px; border-radius: 6px; cursor: pointer;">▶️ Lire</button>
    <button onclick="pauseSpeech()" style="background-color: #f0f2f6; border: 1px solid #d6d6d6; padding: 6px 14px; border-radius: 6px; cursor: pointer;">⏸️ Pause</button>
</div>
<script>
function playSpeech() {{
    window.parent.window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance("{derniere_reponse_clean}");
    u.lang = 'fr-FR';
    window.parent.window.speechSynthesis.speak(u);
}}
function pauseSpeech() {{ window.parent.window.speechSynthesis.cancel(); }}
</script>
"""
components.html(audio_html, height=40)

# --- ZONE DE SAISIE & BOUTON MICRO / CARRÉ ---
# On utilise un conteneur propre pour la saisie textuelle et vocale
col_input, col_mic, col_stop = st.columns([6, 1, 1])

with col_input:
    # Champ texte classique lié au session_state
    prompt_saisi = st.text_input("Message...", value=st.session_state.input_text, label_visibility="collapsed", placeholder="Écrivez ou utilisez le micro...")

# Callback pour mettre à jour l'état si l'utilisateur tape au clavier
st.session_state.input_text = prompt_saisi

# Script JavaScript injecté pour la reconnaissance vocale qui stocke directement dans un input dédié ou interagit proprement
voice_js = """
<div style="display: flex; gap: 5px; justify-content: center;">
    <button onclick="startRec()" style="background-color: #ff4b4b; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 16px;" title="Parler">🎤</button>
    <button onclick="stopRec()" style="background-color: #6c757d; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 16px;" title="Arrêter">⏹️</button>
</div>
<script>
let recognition = null;
function startRec() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { alert("Non supporté"); return; }
    recognition = new SpeechRecognition();
    recognition.lang = 'fr-FR';
    recognition.interimResults = true;
    recognition.continuous = true;
    
    recognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            transcript += event.results[i][0].transcript;
        }
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        if (inputs.length > 0) {
            const target = inputs[0]; // Cible le premier input texte principal
            target.value = transcript;
            target.dispatchevent ? target.dispatchevent(new Event('input', { bubbles: true })) : target.fireEvent('oninput');
        }
    };
    recognition.start();
}
function stopRec() {
    if (recognition) { recognition.stop(); }
}
</script>
"""

with col_mic:
    components.html(voice_js, height=50)

with col_stop:
    envoyer = st.button("Envoyer 📤", use_container_width=True)

# Traitement de l'envoi
if envoyer and st.session_state.input_text:
    texte_final = st.session_state.input_text
    st.session_state.input_text = "" # Reset
    
    db_manager.save_message(st.session_state.session_id, "user", texte_final)
    with st.chat_message("user"):
        if image_file: 
            st.image(image_file, width=200)
        st.write(texte_final)
    
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
