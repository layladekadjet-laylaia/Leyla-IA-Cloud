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
    st.markdown("### 💬 Historique & Actions")
    
    sessions_enregistrees = db_manager.get_all_sessions()
    
    for s_id, s_name in sessions_enregistrees:
        is_active = (s_id == st.session_state.session_id)
        
        col_btn, col_rename, col_del = st.columns([0.65, 0.17, 0.17])
        
        with col_btn:
            prefix = "📌 " if is_active else ""
            if st.button(f"{prefix}{s_name}", key=f"sel_{s_id}", use_container_width=True):
                if not is_active:
                    st.session_state.session_id = s_id
                    st.rerun()
                    
        with col_rename:
            if st.button("✏️", key=f"ren_{s_id}", help="Renommer"):
                st.session_state[f"editing_{s_id}"] = True
                
        with col_del:
            if st.button("🗑️", key=f"del_{s_id}", help="Supprimer"):
                db_manager.delete_session(s_id)
                if is_active:
                    st.session_state.session_id = str(uuid.uuid4())[:8]
                st.rerun()
                
        if st.session_state.get(f"editing_{s_id}", False):
            nouveau_nom = st.text_input("Nouveau nom :", value=s_name, key=f"input_ren_{s_id}")
            col_val, col_ann = st.columns(2)
            with col_val:
                if st.button("Valider", key=f"val_{s_id}"):
                    if nouveau_nom:
                        db_manager.rename_session(s_id, nouveau_nom)
                        st.session_state[f"editing_{s_id}"] = False
                        st.rerun()
            with col_ann:
                if st.button("Annuler", key=f"ann_{s_id}"):
                    st.session_state[f"editing_{s_id}"] = False
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

# --- CONTRÔLES VOCAUX DISCRETS ---
col_v1, col_v2, col_v3, col_v4, col_v5 = st.columns([1, 1, 1, 1, 6])
with col_v1:
    btn_ecouter = st.button("🔊", help="Écouter")
with col_v2:
    btn_parler = st.button("🎙️", help="Parler à Leyla")
with col_v3:
    btn_stop = st.button("⏹️", help="Stop")
with col_v4:
    btn_play = st.button("▶️", help="Play")

# Logique optionnelle pour les boutons vocaux (vous pourrez y lier vos scripts JS si besoin)
if btn_ecouter:
    st.toast("Mode écoute activé")
if btn_parler:
    st.toast("Leyla vous écoute...")
if btn_stop:
    components.html("""<script>window.parent.window.speechSynthesis.cancel();</script>""", height=0)
    st.toast("Lecture arrêtée")
if btn_play:
    st.toast("Lecture en cours...")

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
        reponse_image_path = resultat_ia.get("image_path")
        
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
