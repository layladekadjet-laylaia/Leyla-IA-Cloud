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
    if st.button("➕ Nouvelle Discussion", use_container_width=True): 
        st.session_state.session_id = str(uuid.uuid4())[:8]
        if 'camera_input' in st.session_state:
            del st.session_state['camera_input']
        st.rerun()
        
    activer_voix = st.checkbox("Réponse vocale", value=True)
    
    st.markdown("---")
    st.markdown("### 💬 Historique des Discussions")
    
    # On récupère toutes les sessions de la base de données
    sessions_enregistrees = db_manager.get_all_sessions()
    
    # On affiche chaque session sous forme de bouton dans la sidebar
    for s_id in sessions_enregistrees:
        # Libellé du bouton (on peut personnaliser ici)
        label_bouton = f"Discussion #{s_id}"
        
        # Si c'est la session active, on met une petite mise en valeur visuelle
        if s_id == st.session_state.session_id:
            if st.button(f"📌 {label_bouton}", key=f"sess_{s_id}", use_container_width=True):
                pass # Déjà sur cette session
        else:
            if st.button(label_bouton, key=f"sess_{s_id}", use_container_width=True):
                st.session_state.session_id = s_id
                st.rerun()

    st.markdown("---")
    st.markdown("### 🎨 Studio Créatif")
    choix_source = st.radio("Source média :", ["Aucune", "📁 Fichier", "📷 Caméra"], horizontal=True)
    media_file = None
    if choix_source == "📁 Fichier": 
        media_file = st.file_uploader("Fichier", type=["jpg", "jpeg", "png"])
    elif choix_source == "📷 Caméra": 
        media_file = st.camera_input("Photo")


# --- HISTORIQUE ---
messages = db_manager.get_history(st.session_state.session_id)
for m in messages:
    if m["role"] != "system":
        with st.chat_message(m["role"]): 
            content = m["content"]
            match_img = re.search(r'\[IMAGE:(.*?)\]', content)
            if match_img:
                img_path = match_img.group(1)
                clean_text = re.sub(r'\[IMAGE:.*?\]', '', content).strip()
                if clean_text: st.write(clean_text)
                if os.path.exists(img_path): st.image(img_path, use_container_width=True)
            else:
                st.write(content)

# --- ZONE DE SAISIE ET MOTEUR ---
prompt_saisi = st.chat_input("Écrivez ou utilisez le micro...")
if prompt_saisi:
    st.session_state.message_en_cours = prompt_saisi

if st.session_state.message_en_cours:
    texte_final = st.session_state.message_en_cours
    st.session_state.message_en_cours = "" 
    
    with st.chat_message("user"):
        st.write(texte_final)
    db_manager.save_message(st.session_state.session_id, "user", texte_final)
    
    with st.chat_message("assistant"):
        # APPEL DU MOTEUR
        resultat_ia = rechercher_sur_le_web(db_manager.get_history(st.session_state.session_id), image_file=media_file)
        
        # SÉCURISATION DU RÉSULTAT
        reponse_texte = resultat_ia.get("texte", "...")
        reponse_image_path = resultat_ia.get("image_path") # Sécurisé avec .get()
        
        st.write(reponse_texte)
        
        contenu_a_sauvegarder = reponse_texte
        if reponse_image_path and os.path.exists(reponse_image_path):
            st.image(reponse_image_path, caption="Création Leyla", use_container_width=True)
            contenu_a_sauvegarder += f" [IMAGE:{reponse_image_path}]"
            
        db_manager.save_message(st.session_state.session_id, "assistant", contenu_a_sauvegarder)
        
        # Audio
        if activer_voix:
            t = re.sub(r'[\n\r]+', ' ', reponse_texte).replace('"', '\\"')
            components.html(f"""<script>window.parent.window.speechSynthesis.speak(new SpeechSynthesisUtterance("{t}"));</script>""", height=0)
    st.rerun()
