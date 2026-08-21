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

if 'message_en_cours' not in st.session_state:
    st.session_state.message_en_cours = ""

# --- SIDEBAR ---
with st.sidebar:
    if st.button("➕ Nouvelle Discussion"): 
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.rerun()
        
    activer_voix = st.checkbox("Réponse vocale", value=True)
    
    st.markdown("---")
    st.markdown("### 🎨 Studio Créatif Unifié")
    st.markdown("<small>Tapez simplement ce que vous voulez (recherche, image, code...)</small>", unsafe_allow_html=True)
    
    st.markdown("---")
    choix_source = st.radio("Source média (optionnelle) :", ["Aucune", "📁 Fichier", "📷 Caméra"], horizontal=True)
    media_file = None
    if choix_source == "📁 Fichier": 
        media_file = st.file_uploader("Image ou Vidéo", type=["jpg", "jpeg", "png", "mp4", "mov", "avi", "mkv"])
    elif choix_source == "📷 Caméra": 
        media_file = st.camera_input("Prendre une photo")

# --- HISTORIQUE (Avec persistance des images) ---
messages = db_manager.get_history(st.session_state.session_id)
for m in messages:
    if m["role"] != "system":
        with st.chat_message(m["role"]): 
            content = m["content"]
            # Vérifie si le message contient une balise d'image sauvegardée [IMAGE:chemin]
            match_img = re.search(r'\[IMAGE:(.*?)\]', content)
            if match_img:
                img_path = match_img.group(1)
                # On retire la balise du texte affiché à l'écran
                clean_text = re.sub(r'\[IMAGE:.*?\]', '', content).strip()
                if clean_text:
                    st.write(clean_text)
                if os.path.exists(img_path):
                    st.image(img_path, caption="Création par Leyla IA", use_container_width=True)
                else:
                    st.info("[Image archivée introuvable localement]")
            else:
                st.write(content)

derniere_reponse = next((m["content"] for m in reversed(messages) if m["role"] == "assistant"), "")
derniere_reponse_clean = re.sub(r'\[IMAGE:.*?\]', '', derniere_reponse)
derniere_reponse_clean = re.sub(r'[\n\r]+', ' ', derniere_reponse_clean).replace('"', '\\"')

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

# --- CONTRÔLE VOCAL ---
voice_html = """
<div style="display: flex; justify-content: center; align-items: center; gap: 10px; margin-bottom: 10px;">
    <button onclick="startRec()" id="mic-btn" style="background-color: #ff4b4b; color: white; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold;">🎤 Parler</button>
    <button onclick="stopAndSend()" id="stop-btn" style="background-color: #6c757d; color: white; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold;" disabled>⏹️ Stop & Envoyer</button>
</div>
<script>
let recognition = null;
let fullText = "";
function startRec() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { alert("Non supporté"); return; }
    recognition = new SpeechRecognition();
    recognition.lang = 'fr-FR';
    recognition.interimResults = false;
    recognition.continuous = true;
    fullText = "";
    const micBtn = document.getElementById('mic-btn');
    const stopBtn = document.getElementById('stop-btn');
    recognition.onstart = function() {
        micBtn.style.backgroundColor = "#ffc107";
        micBtn.innerText = "👂 Écoute...";
        stopBtn.style.backgroundColor = "#ff4b4b";
        stopBtn.removeAttribute('disabled');
    };
    recognition.onresult = function(event) {
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                fullText += event.results[i][0].transcript + " ";
            }
        }
        updateChatInput(fullText.trim());
    };
    recognition.onerror = function() { resetUI(); };
    recognition.start();
}
function updateChatInput(text) {
    const chatInput = window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
    if (chatInput) {
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.parent.HTMLTextAreaElement.prototype, "value").set;
        nativeInputValueSetter.call(chatInput, text);
        chatInput.dispatchEvent(new Event('input', { bubbles: true }));
        chatInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
}
function stopAndSend() {
    if (recognition) { recognition.stop(); }
    updateChatInput(fullText.trim());
    setTimeout(() => {
        const submitBtn = window.parent.document.querySelector('button[data-testid="stChatInputSubmitButton"]');
        if (submitBtn) {
            submitBtn.click();
        } else {
            const chatInput = window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
            if (chatInput) {
                chatInput.focus();
                chatInput.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, keyCode: 13, key: 'Enter' }));
            }
        }
    }, 300);
    resetUI();
}
function resetUI() {
    const micBtn = document.getElementById('mic-btn');
    const stopBtn = document.getElementById('stop-btn');
    if (micBtn) { micBtn.style.backgroundColor = "#ff4b4b"; micBtn.innerText = "🎤 Parler"; }
    if (stopBtn) { stopBtn.style.backgroundColor = "#6c757d"; stopBtn.setAttribute('disabled', 'true'); }
}
</script>
"""
components.html(voice_html, height=60)

# --- ZONE DE SAISIE NATIVE ---
prompt_saisi = st.chat_input("Écrivez ou utilisez le micro...")

if prompt_saisi:
    st.session_state.message_en_cours = prompt_saisi

if st.session_state.message_en_cours:
    texte_final = st.session_state.message_en_cours
    st.session_state.message_en_cours = "" 
    
    with st.chat_message("user"):
        if media_file:
            file_type = media_file.type
            if "video" in file_type:
                st.video(media_file)
            else:
                st.image(media_file, width=200)
        st.write(texte_final)
    
    db_manager.save_message(st.session_state.session_id, "user", texte_final)
    
    with st.chat_message("assistant"):
        # Appel du moteur unifié
        resultat_ia = rechercher_sur_le_web(db_manager.get_history(st.session_state.session_id), image_file=media_file)
        
        reponse_texte = resultat_ia["texte"]
        reponse_image_path = resultat_ia.get("image_path", None)

        
        # Affichage du texte
        st.write(reponse_texte)
        
        # Préparation du contenu à enregistrer en base de données avec la balise image si elle existe
        contenu_a_sauvegarder = reponse_texte
        if reponse_image_path:
            st.image(reponse_image_path, caption="Création par Leyla IA", use_container_width=True)
            contenu_a_sauvegarder += f" [IMAGE:{reponse_image_path}]"
            
        db_manager.save_message(st.session_state.session_id, "assistant", contenu_a_sauvegarder)
        
        if activer_voix:
            t = re.sub(r'[\n\r]+', ' ', reponse_texte).replace('"', '\\"')
            components.html(f"""
                <script>
                    window.parent.window.speechSynthesis.cancel();
                    var u = new SpeechSynthesisUtterance('{t}');
                    u.lang = 'fr-FR';
                    window.parent.window.speechSynthesis.speak(u);
                </script>
            """, height=0)
    st.rerun()
