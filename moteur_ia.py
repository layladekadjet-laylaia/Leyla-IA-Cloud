import streamlit as st
from recherche_ia import rechercher_sur_le_web

st.set_page_config(page_title="Leyla IA", page_icon="🤖")

try:
    st.image("LOGO LAYLA.png", width=350)
except Exception:
    pass

st.title("🤖 Leyla IA - Recherche Web")
st.write("Posez une question, Leyla ira chercher l'information pour vous.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage de l'historique
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie
if prompt := st.chat_input("Que voulez-vous savoir ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Leyla cherche sur le web..."):
            reponse = rechercher_sur_le_web(prompt)
            st.markdown(reponse)
    
    st.session_state.messages.append({"role": "assistant", "content": reponse})
