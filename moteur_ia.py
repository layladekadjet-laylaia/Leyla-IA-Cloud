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

# --- CSS (Design épuré) ---
st.markdown(f"""
<style>
    .stApp {{ background-color: #ffffff; }}
    .stApp::before {{ content: ""; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 300px; height: 300px; background-image: url("data:image/png;base64,{img_base64}"); background-repeat: no-repeat; opacity: 0.1; pointer-events: none; z-index: 0; }}
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

# --- HISTORIQUE ---
msgs_hist = db_manager.get_history(st.session_state.session_id)
for m in msgs_hist:
    if m["role"] != "system":
        with st.chat_message(m["role"]): st.write(m["content"])

derniere_reponse = next((m["content"] for m in reversed(msgs_hist) if m["role"] == "assistant"), "")
derniere_reponse_clean = re.sub(r'[\n\r]+', ' ', derniere_reponse).replace('"', '\\"')

# --- BARRE D'OUTILS UNIFIÉE (MICRO, PLAY, PAUSE SUR UNE LIGNE) ---
toolbar_html = f"""
<div style="display: flex; justify-content: center; gap: 10px; margin-bottom: 20px;">
    <button onclick="toggleListening()" id="mic-btn" style="background-color: #ff4b4b; color: white; border: none; padding: 10px 20px; border-radius: 10px; cursor: pointer; font-size: 18px;">🎤</button>
    <button onclick="playSpeech()" style="background-color: #f0f2f6; border: none; padding: 10px 20px; border-radius: 10px; cursor: pointer; font-size: 18px;">▶️</button>
    <button onclick="pauseSpeech()" style="background-color: #f0f2f6; border: none; padding: 10px 20px; border-radius: 10px; cursor: pointer; font-size: 18px;">⏸️</button>
</div>

<script>
let recognition = null;
let isListening = false;

function toggleListening() {{
    const micBtn = document.getElementById('mic-btn');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {{ alert("Non supporté"); return; }}
    
    if (isListening) {{ if (recognition) recognition.stop(); return; }}

    recognition = new SpeechRecognition();
    recognition.lang = 'fr-FR';
    recognition.interimResults = true;
    recognition.continuous = true;

    recognition.onstart = () => {{ isListening = true; micBtn.style.backgroundColor = "#ffc107"; }};
    recognition.onresult = (event) => {{
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) transcript += event.results[i][0].transcript;
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        if (inputs.length > 0) {{
            const target = inputs[inputs.length - 1];
            target.value = transcript;
            target.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
    }};
    recognition.onend = () => {{ isListening = false; micBtn.style.backgroundColor = "#ff4b4b"; }};
    recognition.start();
}}

function playSpeech() {{ 
    window.parent.window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance("{derniere_reponse_clean}");
    u.lang = 'fr-FR';
    window.parent.window.speechSynthesis.speak(u);
}}
function pauseSpeech() {{ window.parent.window.speechSynthesis.cancel(); }}
</script>
"""
components.html(toolbar_html, height=70)

# --- ZONE DE SAISIE (Formulaire propre) ---
with st.form(key="chat_form", clear_on_submit=True):
    prompt = st.text_input("Parlez avec le micro ou écrivez ici...", label_visibility="collapsed")
    submit = st.form_submit_button("Envoyer 📤")

if submit and prompt:
    db_manager.save_message(st.session_state.session_id, "user", prompt)
    with st.chat_message("user"): st.write(prompt)
    with st.chat_message("assistant"):
        reponse = rechercher_sur_le_web(db_manager.get_history(st.session_state.session_id))
        st.write(reponse)
        db_manager.save_message(st.session_state.session_id, "assistant", reponse)
        if activer_voix:
            components.html(f"<script>window.parent.speechSynthesis.speak(new SpeechSynthesisUtterance('{reponse.replace(chr(10), ' ').replace("'", "\\'")}'));</script>", height=0)
    st.rerun()
