import base64
import os
import re
import uuid
import db_manager
from recherche_ia import rechercher_sur_le_web
import streamlit as st
import streamlit.components.v1 as components
import utils_memoire

# --- INITIALISATION ET CONFIGURATION ---
db_manager.init_db()
st.set_page_config(
    page_title="Leyla IA - Assistant Personnel", page_icon="🤖", layout="centered"
)


# --- CHARGEMENT DU LOGO EN BASE64 ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""


img_base64 = get_base64_image("LOGO LAYLA.png")

# --- CSS PERSONNALISÉ & FILIGRANE ---
st.markdown(
    f"""
<style>
    .stApp {{ background-color: #ffffff; }}
    .stApp::before {{
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 280px;
        height: 280px;
        background-image: url("data:image/png;base64,{img_base64}");
        background-repeat: no-repeat;
        background-size: contain;
        opacity: 0.12;
        pointer-events: none;
        z-index: 0;
    }}
</style>
""",
    unsafe_allow_html=True,
)

# --- IDENTIFICATION UTILISATEUR ---
user_name = db_manager.get_user_name()
if not user_name:
    st.title("🤖 Bienvenue sur Leyla IA")
    nom_saisi = st.text_input(
        "Comment dois-je vous appeler, Mon Professeur ?"
    )
    if nom_saisi:
        db_manager.save_user_name(nom_saisi)
        st.rerun()
    st.stop()

# --- INITIALISATION DE LA SESSION ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "message_en_cours" not in st.session_state:
    st.session_state.message_en_cours = ""

# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.title("⚡ Leyla Control")
    if st.button("➕ Nouvelle Discussion", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        if "camera_input" in st.session_state:
            del st.session_state["camera_input"]
        st.rerun()

    activer_voix = st.checkbox("🔊 Réponse vocale automatique", value=True)

    st.markdown("---")
    st.markdown("### 💬 Sessions")

    sessions_enregistrees = db_manager.get_all_sessions()

    for s_id, s_name in sessions_enregistrees:
        is_active = s_id == st.session_state.session_id
        col_btn, col_rename, col_del = st.columns([0.65, 0.17, 0.17])

        with col_btn:
            prefix = "📌 " if is_active else ""
            if st.button(
                f"{prefix}{s_name}", key=f"sel_{s_id}", use_container_width=True
            ):
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
            nouveau_nom = st.text_input(
                "Nom :", value=s_name, key=f"input_ren_{s_id}"
            )
            col_val, col_ann = st.columns(2)
            with col_val:
                if st.button("OK", key=f"val_{s_id}"):
                    if nouveau_nom:
                        db_manager.rename_session(s_id, nouveau_nom)
                        st.session_state[f"editing_{s_id}"] = False
                        st.rerun()
            with col_ann:
                if st.button("X", key=f"ann_{s_id}"):
                    st.session_state[f"editing_{s_id}"] = False
                    st.rerun()

    st.markdown("---")
    st.markdown("### 🎨 Studio Créatif / Vision")
    choix_source = st.radio(
        "Source média :", ["Aucune", "📁 Fichier", "📷 Caméra"], horizontal=True
    )
    media_file = None
    if choix_source == "📁 Fichier":
        media_file = st.file_uploader(
            "Téléverser une image", type=["jpg", "jpeg", "png"]
        )
    elif choix_source == "📷 Caméra":
        media_file = st.camera_input("Prendre une photo")

# --- AFFICHAGE DE L'HISTORIQUE ---
messages = db_manager.get_history(st.session_state.session_id)
for m in messages:
    if m["role"] != "system":
        with st.chat_message(m["role"]):
            content = m["content"]
            match_img = re.search(r"\[IMAGE:(.*?)\]", content)
            if match_img:
                img_path = match_img.group(1)
                clean_text = re.sub(r"\[IMAGE:.*?\]", "", content).strip()
                if clean_text:
                    st.write(clean_text)
                if os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
            else:
                st.write(content)

# --- CONTRÔLES VOCAUX INTERACTIFS ---
col_v1, col_v2, col_v3, col_v4 = st.columns([1, 1, 1, 5])
with col_v1:
    btn_parler = st.button("🎙️", help="Dictée vocale (Micro)")
with col_v2:
    btn_stop = st.button("⏹️", help="Arrêter la parole")
with col_v3:
    if st.button("🧠", help="Mettre à jour la mémoire long terme"):
        utils_memoire.extraire_et_sauvegarder_faits(messages)
        st.toast("Mémoire de Leyla synchronisée !")

if btn_stop:
    components.html(
        """<script>window.parent.window.speechSynthesis.cancel();</script>""",
        height=0,
    )

if btn_parler:
    # JS pour la reconnaissance vocale Web Speech API
    components.html(
        """
        <script>
            var recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'fr-FR';
            recognition.onresult = function(event) {
                var text = event.results[0][0].transcript;
                var chatInput = window.parent.document.querySelector('textarea[aria-label="Écrivez ou utilisez le micro..."]');
                if (chatInput) {
                    chatInput.value = text;
                    chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            };
            recognition.start();
        </script>
    """,
        height=0,
    )

# --- SAISIE ET TRAITEMENT DU MOTEUR ---
prompt_saisi = st.chat_input("Écrivez ou utilisez le micro...")
if prompt_saisi:
    st.session_state.message_en_cours = prompt_saisi

if st.session_state.message_en_cours:
    texte_final = st.session_state.message_en_cours
    st.session_state.message_en_cours = ""

    # 1. Enregistrement et affichage du message utilisateur
    with st.chat_message("user"):
        st.write(texte_final)
    db_manager.save_message(st.session_state.session_id, "user", texte_final)

    # 2. Traitement par Leyla
    with st.chat_message("assistant"):
        historique_actuel = db_manager.get_history(st.session_state.session_id)

        # Appel du moteur révisé avec recherche Web et Imagen 3
        resultat_ia = rechercher_sur_le_web(
            historique_actuel, image_file=media_file
        )

        reponse_texte = resultat_ia.get("texte", "...")
        reponse_image_path = resultat_ia.get("image_path")

        st.write(reponse_texte)

        contenu_a_sauvegarder = reponse_texte
        if reponse_image_path and os.path.exists(reponse_image_path):
            st.image(
                reponse_image_path,
                caption="Création de Leyla",
                use_container_width=True,
            )
            contenu_a_sauvegarder += f" [IMAGE:{reponse_image_path}]"

        db_manager.save_message(
            st.session_state.session_id, "assistant", contenu_a_sauvegarder
        )

        # 3. Synchronisation de la mémoire à long terme
        utils_memoire.extraire_et_sauvegarder_faits(
            db_manager.get_history(st.session_state.session_id)
        )

        # 4. Synthesize vocale (TTS)
        if activer_voix:
            texte_vocale = re.sub(r"[\*\#\_\`\~]", "", reponse_texte)
            texte_vocale = (
                re.sub(r"[\n\r]+", " ", texte_vocale)
                .replace('"', '\\"')
                .replace("'", "\\'")
            )
            components.html(
                f"""<script>
                window.parent.window.speechSynthesis.cancel();
                var msg = new SpeechSynthesisUtterance("{texte_vocale}");
                msg.lang = 'fr-FR';
                window.parent.window.speechSynthesis.speak(msg);
            </script>""",
                height=0,
            )

    st.rerun()
