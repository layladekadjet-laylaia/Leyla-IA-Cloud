import streamlit as st
from recherche_ia import rechercher_sur_le_web
import db_manager

# Initialisation de la base de données SQLite
db_manager.init_db()

st.set_page_config(page_title="Leyla IA", page_icon="🤖")

try:
    st.image("LOGO LAYLA.png", width=350)
except Exception:
    pass

st.title("🤖 Leyla IA - Mémoire SQLite")
st.write("Posez une question, Leyla ira chercher l'information pour vous.")

# Récupération de l'historique depuis la base de données SQLite
messages = db_manager.get_history()

# Affichage de l'historique
for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie
if prompt := st.chat_input("Que voulez-vous savoir ?"):
    # 1. Sauvegarder la question de l'utilisateur en BDD
    db_manager.save_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Recharger l'historique complet (incluant le nouveau prompt) pour l'IA
    messages_actuels = db_manager.get_history()

    with st.chat_message("assistant"):
        with st.spinner("Leyla cherche sur le web..."):
            # L'IA analyse toute la conversation grâce à la BDD et DuckDuckGo
            reponse = rechercher_sur_le_web(messages_actuels)
            st.markdown(reponse)
    
    # 3. Sauvegarder la réponse de l'assistant en BDD
    db_manager.save_message("assistant", reponse)
