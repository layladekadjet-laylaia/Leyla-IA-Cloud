import streamlit as st
from recherche_ia import rechercher_sur_le_web
import db_manager
from gtts import gTTS
import os

# Initialisation de la base de données SQLite
db_manager.init_db()

st.set_page_config(page_title="Leyla IA", page_icon="🤖", layout="centered")

# --- PERSONNALISATION CSS STYLE CLAIR (BLANC) ---
st.markdown("""
<style>
    /* Style général : Fond blanc éclatant et texte sombre */
    .stApp {
        background-color: #ffffff;
        color: #1f1f1f;
    }
    /* Style des bulles de chat en mode clair */
    .stChatMessage {
        border-radius: 16px;
        padding: 12px 16px;
        margin-bottom: 10px;
        background-color: #f8f9fa;
        border: 1px solid #e5e5e5;
    }
    /* Zone de saisie arrondie */
    .stChatInputContainer input {
        border-radius: 24px !important;
        background-color: #f0f4f9 !important;
        color: #1f1f1f !important;
        border: 1px solid #c4c7c5 !important;
    }
    /* Textes et titres en mode clair */
    h1, h2, h3, p, label {
        color: #1f1f1f !important;
    }
</style>
""", unsafe_allow_html=True)

# En-tête avec logo
try:
    st.image("LOGO LAYLA.png", width=250)
except Exception:
    pass

st.title("Leyla IA")
st.caption("Votre assistant intelligent, conçu par Djè Akadjé pour Mon Professeur.")

# Barre latérale pour les paramètres
with st.sidebar:
    st.header("Paramètres")
    activer_voix = st.checkbox("Activer la réponse vocale", value=True)
    st.markdown("---")
    st.write("Mode Clair & Mémoire SQLite actif.")

# Récupération de l'historique depuis la base de données SQLite
messages = db_manager.get_history()

# Affichage de l'historique des messages avec des avatars distincts
for message in messages:
    avatar_icon = "👨‍💻" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])

# --- GESTION DES ENTRÉES : TEXTE ET FICHIER/IMAGE ---
image_uploadee = st.file_uploader("Ajouter une image ou un fichier de diagnostic", type=["jpg", "jpeg", "png"])

if prompt := st.chat_input("Posez votre question à Leyla..."):
    
    contenu_utilisateur = prompt
    if image_uploadee is not None:
        image_path = "temp_image.png"
        with open(image_path, "wb") as f:
            f.write(image_uploadee.getbuffer())
        
        with st.chat_message("user", avatar="👨‍💻"):
            st.image(image_uploadee, caption="Image transmise", width=300)
            st.markdown(prompt)
        
        contenu_utilisateur = f"[Image envoyée] {prompt}"
    else:
        with st.chat_message("user", avatar="👨‍💻"):
            st.markdown(prompt)

    # Sauvegarde de la question
    db_manager.save_message("user", contenu_utilisateur)

    # Récupération de l'historique mis à jour
    messages_actuels = db_manager.get_history()

    # Réponse de l'assistant
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Leyla réfléchit..."):
            reponse = rechercher_sur_le_web(messages_actuels)
            st.markdown(reponse)
            
            # Gestion de la synthèse vocale
            if activer_voix:
                try:
                    tts = gTTS(text=reponse, lang='fr', slow=False)
                    audio_path = "reponse_leyla.mp3"
                    tts.save(audio_path)
                    st.audio(audio_path, format="audio/mp3", autoplay=True)
                except Exception as e:
                    st.warning(f"Audio non disponible : {e}")
    
    # Sauvegarde de la réponse
    db_manager.save_message("assistant", reponse)
