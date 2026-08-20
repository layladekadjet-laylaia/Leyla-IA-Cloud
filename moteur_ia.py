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

# --- BARRE DE CONTRÔLE AUDIO (PLAY / PAUSE SEULS) ---
audio_controls_html = f"""
<div style="display: flex; justify-content: center; gap: 15px; align-items: center; margin: 10px 0 5px 0;">
    <button onclick="playSpeech()" style="background-color: #f0f2f6; color: #31333F; border: 1px solid #d6d6d6; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 18px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">▶️</button>
    <button onclick="pauseSpeech()" style="background-color: #f0f2f6; color: #31333F; border: 1px solid #d6d6d6; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 18px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">⏸️</button>
</div>

<script>
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
components.html(audio_controls_html, height=50)

# --- MODULE DE DICTÉE VOCALE DIRECTE ET CHAMP DE SAISIE ---
# On intègre le bouton micro directement à côté de la zone de saisie pour qu'ils ne fassent qu'un
st.markdown("""
<div id="mic-container" style="display: flex; gap: 10px; align-items: center; margin-bottom: -10px;">
    <button type="button" onclick="toggleSpeechRecognition()" id="inline-mic-btn" style="background-color: #ff4b4b; color: white; border: none; padding: 10px 14px; border-radius: 8px; cursor: pointer; font-size: 18px; height: 42px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" title="Activer le micro">🎤</button>
</div>

<script>
let recognitionInstance = null;
let recordingActive = false;

function toggleSpeechRecognition() {
    const btn = document.getElementById('inline-mic-btn');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        alert("La reconnaissance vocale n'est pas supportée par ce navigateur.");
        return;
    }

    if (recordingActive) {
        if (recognitionInstance) recognitionInstance.stop();
        return;
    }

    recognitionInstance = new SpeechRecognition();
    recognitionInstance.lang = 'fr-FR';
    recognitionInstance.interimResults = true;
    recognitionInstance.continuous = true;

    recognitionInstance.onstart = function() {
        recordingActive = true;
        btn.style.backgroundColor = "#ffc107"; // Jaune = En écoute active
    };

    recognitionInstance.onresult = function(event) {
        let currentTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            currentTranscript += event.results[i][0].transcript;
        }

        // Injection en direct dans le champ de saisie Streamlit
        const doc = window.parent.document;
        const textInputs = doc.querySelectorAll('input[type="text"]');
        if (textInputs.length > 0) {
            const activeInput = textInputs[textInputs.length - 1];
            activeInput.value = currentTranscript;
            activeInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
    };

    recognitionInstance.onend = function() {
        recordingActive = false;
        btn.style.backgroundColor = "#ff4b4b"; // Retour au rouge
    };

    recognitionInstance.onerror = function() {
        recordingActive = false;
        btn.style.backgroundColor = "#ff4b4b";
    };

    recognitionInstance.start();
}
</script>
""", unsafe_allow_html=True)

# Zone de saisie manuelle associée au formulaire d'envoi
with st.form(key="unified_chat_form", clear_on_submit=True):
    col_input, col_submit = st.columns([6, 1])
    with col_input:
        prompt = st.text_input("Que voulez-vous savoir ?", label_visibility="collapsed", placeholder="Parlez avec le micro ou écrivez ici...")
    with col_submit:
        submit_button = st.form_submit_button("📤")

if submit_button and prompt:
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
