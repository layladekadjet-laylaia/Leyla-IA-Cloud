import base64
import os
import re
import socket
import uuid
import db_manager
from recherche_ia import rechercher_sur_le_web
import streamlit as st
import streamlit.components.v1 as components
import utils_memoire

# --- CONFIGURATION DU SERVEUR HUB (RÉSEAU LOCAL WI-FI PC) ---
# IP IPv4 exacte de votre PC sur le réseau Wi-Fi : 192.168.100.75
IP_SERVEUR_HUB = "192.168.100.75"
PORT_SERVEUR_HUB = 8000
URL_HUB_WEBSOCKET = f"ws://{IP_SERVEUR_HUB}:{PORT_SERVEUR_HUB}/ws"


def verifier_hub_disponible(ip: str, port: int, timeout: float = 1.0) -> bool:
    """Vérifie si le serveur Hub est joignable sur le réseau local sans bloquer l'application."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        resultat = sock.connect_ex((ip, port))
        sock.close()
        return resultat == 0
    except Exception:
        return False


# --- IMPORTATION DES MODULES JARVIS ---
try:
    from camera_leyla import capturer_et_analyser_camera_externe
except ImportError:
    capturer_et_analyser_camera_externe = None

try:
    from briefing_leyla import generer_briefing_matinal
except ImportError:
    generer_briefing_matinal = None

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
    nom_saisi = st.text_input("Comment dois-je vous appeler, Mon Professeur ?")
    if nom_saisi:
        db_manager.save_user_name(nom_saisi)
        st.rerun()
    st.stop()

# --- INITIALISATION DE LA SESSION ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "message_en_cours" not in st.session_state:
    st.session_state.message_en_cours = ""

# --- BARRE LATÉRALE (SIDEBAR - CONTRÔLEUR JARVIS) ---
with st.sidebar:
    st.title("⚡ Leyla Control")
    if st.button("➕ Nouvelle Discussion", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        if "camera_input" in st.session_state:
            del st.session_state["camera_input"]
        st.rerun()

    activer_voix = st.checkbox("🔊 Réponse vocale automatique", value=True)

    # --- FONCTIONNALITÉS JARVIS ---
    st.markdown("---")
    st.markdown("### 👑 Fonctions JARVIS")

    # Étape 1 : Wake Word
    if st.button("🎧 Écoute Passive (Wake Word)", use_container_width=True):
        st.toast(
            "Pour activer l'écoute passive sur mobile, utilisez ecoute_leyla_mobile.py"
        )

    # Étape 2 : Briefing Matinal
    if st.button("🌅 Briefing Matinal Proactif", use_container_width=True):
        if generer_briefing_matinal:
            with st.spinner("Génération de votre briefing, Mon Professeur..."):
                briefing = generer_briefing_matinal()
                st.session_state.message_en_cours = briefing
                st.rerun()
        else:
            st.error("Module briefing_leyla.py introuvable.")

    # Étape 4 : Mémoire Proactive
    if st.button("🧠 Synchro Mémoire Long Terme", use_container_width=True):
        messages = db_manager.get_history(st.session_state.session_id)
        utils_memoire.extraire_et_sauvegarder_faits(messages)
        st.toast("Mémoire de Leyla synchronisée !")

    # Étape 5 : Hub Multi-Appareils (AJUSTÉ AVEC L'IP PC 192.168.100.75)
    if st.button("📱 État Hub Multi-Appareils", use_container_width=True):
        with st.spinner("Vérification de la connexion au Hub PC..."):
            est_actif = verifier_hub_disponible(
                IP_SERVEUR_HUB, PORT_SERVEUR_HUB, timeout=1.0
            )
            if est_actif:
                st.success(f"Connecté au Hub Leyla : {URL_HUB_WEBSOCKET}")
            else:
                st.warning(
                    f"Hub hors ligne ou inatteignable sur {URL_HUB_WEBSOCKET}.\n"
                    f"Vérifiez que le serveur WebSocket tourne sur le PC."
                )

    # --- SECTION SOURCING MÉDIA & CAMÉRAS ---
    st.markdown("---")
    st.markdown("### 🎨 Studio Visuel & Caméras")
    choix_source = st.radio(
        "Source média :",
        ["Aucune", "📁 Fichier", "📷 Caméra", "📹 Caméra IP (RTSP)"],
        horizontal=False,
    )

    media_file = None
    if choix_source == "📁 Fichier":
        media_file = st.file_uploader(
            "Téléverser une image", type=["jpg", "jpeg", "png"]
        )
    elif choix_source == "📷 Caméra":
        media_file = st.camera_input("Prendre une photo")
    elif choix_source == "📹 Caméra IP (RTSP)":
        rtsp_url = st.text_input(
            "URL du flux (RTSP/HTTP) :",
            placeholder="rtsp://admin:12345@192.168.1.50:554/live",
        )
        if st.button("👁️️ Analyser le Flux Caméra", use_container_width=True):
            if rtsp_url and capturer_et_analyser_camera_externe:
                with st.spinner("Analyse du flux réseau..."):
                    rapport = capturer_et_analyser_camera_externe(rtsp_url)
                    st.session_state.message_en_cours = (
                        f"[ANALYSE CAMÉRA DISTANTE]\n{rapport}"
                    )
                    st.rerun()

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
    btn_parler = st.button("🎙️️", help="Dictée vocale (Micro)")
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

        # 4. Synthèse vocale (TTS)
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
