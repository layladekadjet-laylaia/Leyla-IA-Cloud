import streamlit as st
from recherche_ia import rechercher_sur_le_web
import db_manager
from gtts import gTTS
import os
import base64

# Initialisation de la base de données SQLite
db_manager.init_db()

st.set_page_config(page_title="Leyla IA", page_icon="🤖")

try:
    st.image("LOGO LAYLA.png", width=350)
except Exception:
    pass

st.title("🤖 Leyla IA - Multimédia & Mémoire")
st.write("Posez vos questions, envoyez des images, Leyla vous répond par texte, image et voix !")

# Options de configuration dans la barre latérale
with st.sidebar:
    st.header("Paramètres de Leyla")
    activer_voix = st.checkbox("Activer la réponse vocale", value=True)
    st.markdown("---")
    st.write("Conçu par Djè Akadjé pour Mon Professeur.")

# Récupération de l'historique depuis la base de données SQLite
messages = db_manager.get_history()

# Affichage de l'historique des messages
for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- GESTION DES ENTRÉES : TEXTE ET FICHIER/IMAGE ---
image_uploadee = st.file_uploader("Envoyer une photo ou un fichier à Leyla (ex: diagnostic de plante)", type=["jpg", "jpeg", "png"])

if prompt := st.chat_input("Que voulez-vous savoir, Mon Professeur ?"):
    
    contenu_utilisateur = prompt
    if image_uploadee is not None:
        # Sauvegarde temporaire de l'image pour l'afficher
        image_path = "temp_image.png"
        with open(image_path, "wb") as f:
            f.write(image_uploadee.getbuffer())
        
        # Affichage de l'image dans le chat
        with st.chat_message("user"):
            st.image(image_uploadee, caption="Image envoyée par Mon Professeur", width=300)
            st.markdown(prompt)
        
        contenu_utilisateur = f"[Image envoyée] {prompt}"
    else:
        with st.chat_message("user"):
            st.markdown(prompt)

    # Sauvegarde dans la base de données
    db_manager.save_message("user", contenu_utilisateur)

    # Récupération de l'historique mis à jour
    messages_actuels = db_manager.get_history()

    with st.chat_message("assistant"):
        with st.spinner("Leyla analyse et cherche..."):
            # Appel de la fonction de recherche et d'intelligence
            reponse = rechercher_sur_le_web(messages_actuels)
            st.markdown(reponse)
            
            # Génération de la voix si activée
            if activer_voix:
                try:
                    tts = gTTS(text=reponse, lang='fr', slow=False)
                    audio_path = "reponse_leyla.mp3"
                    tts.save(audio_path)
                    st.audio(audio_path, format="audio/mp3", autoplay=True)
                except Exception as e:
                    st.warning(f"Audio non disponible : {e}")
    
    # Sauvegarde de la réponse de l'assistant
    db_manager.save_message("assistant", reponse)
