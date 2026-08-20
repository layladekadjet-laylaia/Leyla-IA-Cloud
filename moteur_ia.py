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

# --- BARRE DE CONTRÔLE VOCAL CORRIGÉE (Anti-duplication) ---
voice_control_html = """
<div style="display: flex; justify-content: center; align-items: center; gap: 10px; margin-bottom: 5px;">
    <button onclick="startListening()" id="mic-btn" style="background-color: #ff4b4b; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold;">🎤 Parler</button>
    <button onclick="stopAndSend()" id="stop-btn" style="background-color: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold;" disabled>⏹️ Stop & Envoyer</button>
</div>

<script>
let recognition = null;

function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("La reconnaissance vocale n'est pas supportée par ce navigateur.");
        return;
    }
    
    recognition = new SpeechRecognition();
    recognition.lang = 'fr-FR';
    recognition.interimResults = true;
    recognition.continuous = true;

    const micBtn = document.getElementById('mic-btn');
    const stopBtn = document.getElementById('stop-btn');

    recognition.onstart = function() {
        micBtn.style.backgroundColor = "#ffc107";
        micBtn.innerText = "👂 Écoute...";
        stopBtn.style.backgroundColor = "#ff4b4b";
        stopBtn.removeAttribute('disabled');
    };

    recognition.onresult = function(event) {
        // On reconstruit proprement le texte final sans boucler de manière erronée sur les index intermédiaires
        let transcript = '';
        for (let i = 0; i < event.results.length; ++i) {
            transcript += event.results[i][0].transcript;
        }
        
        const chatInput = window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
        if (chatInput) {
            chatInput.value = transcript;
            chatInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
    };
    
    recognition.onerror = function() {
        resetUI();
    };

    recognition.start();
}

function stopAndSend() {
    if (recognition) {
        recognition.stop();
    }
    resetUI();
    
    // Déclenchement propre de l'envoi via la touche Entrée simulée
    setTimeout(() => {
        const chatInput = window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
        if (chatInput) {
            chatInput.focus();
            chatInput.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, keyCode: 13, key: 'Enter' }));
        }
    }, 300);
}

function resetUI() {
    const micBtn = document.getElementById('mic-btn');
    const stopBtn = document.getElementById('stop-btn');
    if (micBtn) {
        micBtn.style.backgroundColor = "#ff4b4b";
        micBtn.innerText = "🎤 Parler";
    }
    if (stopBtn) {
        stopBtn.style.backgroundColor = "#6c757d";
        stopBtn.setAttribute('disabled', 'true');
    }
}
</script>
"""
components.html(voice_control_html, height=55)

# --- ZONE DE SAISIE NATIVE STREAMLIT ---
prompt = st.chat_input("Écrivez ou utilisez le micro ci-dessus...")

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
