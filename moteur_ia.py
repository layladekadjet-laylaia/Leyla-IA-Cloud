import asyncio
import base64
import os
import re
import uuid
import db_manager
from recherche_ia import rechercher_sur_le_web
import streamlit as st
import streamlit.components.v1 as components
import utils_memoire
import utils_scan

# --- INITIALISATION ET CONFIGURATION ---
db_manager.init_db()
st.set_page_config(
    page_title="LEYLA v2.6 // Edge Agent", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CHARGEMENT DU LOGO EN BASE64 ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

img_base64 = get_base64_image("LOGO LAYLA.png")

# --- CSS HAUT CONTRASTE & ÉCRITURES PURES (#FFFFFF) ---
st.markdown(
    f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', sans-serif;
    }}

    /* Fond principal sombre et profond */
    .stApp {{
        background-color: #06090e !important;
        background-image: radial-gradient(ellipse at top, rgba(0, 242, 254, 0.12) 0%, transparent 70%) !important;
        color: #ffffff !important;
    }}

    /* Filigrane central subtil */
    .stApp::before {{
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 320px;
        height: 320px;
        background-image: url("data:image/png;base64,{img_base64}");
        background-repeat: no-repeat;
        background-size: contain;
        opacity: 0.03;
        pointer-events: none;
        z-index: 0;
    }}

    /* Sidebar - Verre poli sombre à fort contraste */
    [data-testid="stSidebar"] {{
        background: rgba(10, 15, 26, 0.95) !important;
        border-right: 1px solid rgba(0, 242, 254, 0.2) !important;
    }}

    /* Forcer tous les textes généraux en Blanc Pur */
    p, span, label, div, h1, h2, h3, h4, .stMarkdown {{
        color: #ffffff !important;
    }}

    /* Titres de section et textes secondaires lisibles */
    .stMarkdown p, .stMarkdown label, [data-testid="stSidebar"] p {{
        color: #e2e8f0 !important;
        font-size: 0.95rem;
    }}

    /* Bulles de chat HAUTE LISIBILITÉ */
    [data-testid="stChatMessage"] {{
        background: rgba(15, 23, 42, 0.9) !important;
        border: 1px solid rgba(0, 242, 254, 0.25) !important;
        border-radius: 14px !important;
        padding: 1.1rem !important;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5) !important;
        margin-bottom: 0.9rem !important;
    }}

    /* Contenu texte du chat en BLANC PUR NET */
    [data-testid="stChatMessage"] p {{
        color: #ffffff !important;
        font-size: 1rem !important;
        line-height: 1.6 !important;
        font-weight: 400 !important;
    }}

    /* Boutons stylisés haute visibilité */
    div.stButton > button {{
        background: rgba(15, 23, 42, 0.95) !important;
        border: 1px solid rgba(0, 242, 254, 0.4) !important;
        color: #00f2fe !important;
        border-radius: 10px !important;
        transition: all 0.2s ease-in-out !important;
        font-weight: 600 !important;
    }}

    div.stButton > button:hover {{
        background: rgba(0, 242, 254, 0.2) !important;
        border-color: #00f2fe !important;
        color: #ffffff !important;
        box-shadow: 0 0 15px rgba(0, 242, 254, 0.4) !important;
    }}

    /* Zone de saisie flottante */
    [data-testid="stChatInput"] {{
        background: rgba(15, 23, 42, 0.95) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(0, 242, 254, 0.4) !important;
    }}

    [data-testid="stChatInput"] textarea {{
        color: #ffffff !important;
    }}

    /* Badges & cartes utilisateur */
    .user-card {{
        padding: 10px 14px;
        border-radius: 8px;
        background: rgba(0, 242, 254, 0.1);
        border: 1px solid rgba(0, 242, 254, 0.3);
        color: #00f2fe !important;
        font-size: 0.9rem;
        font-weight: 600;
    }}

    .telemetry-box {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #cbd5e1 !important;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        padding-top: 12px;
        margin-top: 20px;
    }}

    .indicator-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #00f2fe;
        box-shadow: 0 0 10px #00f2fe;
        display: inline-block;
    }}
</style>
""",
    unsafe_allow_html=True,
)

# --- IMPORTATION DES MODULES ---
try:
    from briefing_leyla import generer_briefing_matinal
except ImportError:
    generer_briefing_matinal = None

# --- IDENTIFICATION UTILISATEUR ---
user_name = db_manager.get_user_name()
if not user_name:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align: center;">
                <div class="indicator-dot" style="width:14px; height:14px; margin-bottom: 10px;"></div>
                <h1 style="margin: 0; font-size: 2rem; color: #00f2fe !important;">LEYLA v2.6</h1>
                <p style="color: #ffffff !important; font-size: 0.95rem; margin-top: 6px;">Initialisation de l'Agent Edge</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        nom_saisi = st.text_input("Comment dois-je vous appeler, Mon Professeur ?", placeholder="Ex: Djè Akadjé")
        if nom_saisi:
            db_manager.save_user_name(nom_saisi)
            st.rerun()
    st.stop()

# --- INITIALISATION DE LA SESSION ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "message_en_cours" not in st.session_state:
    st.session_state.message_en_cours = ""

if "inventaire_reseau" not in st.session_state:
    st.session_state.inventaire_reseau = []

# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
            <div class="indicator-dot"></div>
            <h1 style="font-size: 1.2rem; margin: 0; color: #00f2fe !important; font-weight: 700;">
                LEYLA <span style="font-size: 0.75rem; color: #ffffff; font-weight: 400;">v2.6</span>
            </h1>
        </div>
        <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #00f2fe; font-family: 'JetBrains Mono', monospace; margin-bottom: 6px;">
            UTILISATEUR
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown(
        f'<div class="user-card">Mon Professeur {user_name}</div>', 
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("➕ Nouvelle Discussion", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.rerun()

    activer_voix = st.checkbox("🔊 Réponse vocale automatique", value=True)

    # --- MODULES EXÉCUTIFS ---
    st.markdown("---")
    st.markdown("### 👑 Fonctions LEYLA")

    if st.button("🎧 Écoute Passive (Wake Word)", use_container_width=True):
        st.toast("Pour activer l'écoute passive, utilisez le script mobile dédié.")

    if st.button("🌅 Briefing Matinal Proactif", use_container_width=True):
        if generer_briefing_matinal:
            with st.spinner("Génération du briefing..."):
                briefing = generer_briefing_matinal()
                st.session_state.message_en_cours = briefing
                st.rerun()
        else:
            st.error("Module briefing_leyla.py introuvable.")

    if st.button("🧠 Synchro Mémoire Long Terme", use_container_width=True):
        messages = db_manager.get_history(st.session_state.session_id)
        utils_memoire.extraire_et_sauvegarder_faits(messages)
        st.toast("Mémoire de Leyla synchronisée !")

    # --- DÉCOUVERTE MATÉRIELLE ---
    st.markdown("---")
    st.markdown("### 📱 Découverte Réseau & IoT")

    type_recherche = st.selectbox(
        "Cible de recherche :", ["Bluetooth Proche", "Passerelle & Appareils Wi-Fi (IoT/Caméras)"]
    )

    if st.button("🔍 Lancer le Scan Global", use_container_width=True):
        if type_recherche == "Bluetooth Proche":
            with st.spinner("Analyse du champ Bluetooth..."):
                appareils_bt = asyncio.run(utils_scan.scanner_bluetooth_proche())
                if appareils_bt:
                    st.success(f"{len(appareils_bt)} appareil(s) trouvé(s) :")
                    for dev in appareils_bt:
                        st.info(f"📱 **{dev['nom']}** | `{dev['adresse']}`")
                else:
                    st.warning("Aucun appareil Bluetooth à proximité.")
        else:
            with st.spinner("Cartographie complète du réseau..."):
                rapport = utils_scan.scanner_reseau_complet()
                st.session_state.inventaire_reseau = rapport['appareils']
                infos_routeur = utils_scan.interroger_interface_routeur(rapport['passerelle'])
                st.success(f"Passerelle : `{rapport['passerelle']}` | {rapport['total_appareils']} actif(s)")

    # --- COFFRE-FORT & CAMÉRAS ---
    st.markdown("---")
    with st.expander("🔐 Coffre-fort Caméras / Access IP"):
        ip_cible_cred = st.text_input("Adresse IP", placeholder="192.168.100.50")
        user_cred = st.text_input("Utilisateur", value="admin")
        pass_cred = st.text_input("Mot de passe", type="password")
        if st.button("Enregistrer les accès", use_container_width=True):
            if ip_cible_cred:
                db_manager.save_device_credentials(ip_cible_cred, user_cred, pass_cred)
                st.toast(f"Accès enregistrés pour {ip_cible_cred} !")

    # --- STUDIO MULTIMÉDIA ---
    st.markdown("---")
    st.markdown("### 🎨 Studio Multimédia")
    choix_source = st.radio("Source média :", ["Aucune", "📁 Fichier", "📷 Caméra web"])

    media_file = None
    if choix_source == "📁 Fichier":
        media_file = st.file_uploader("Fichier", type=["jpg", "jpeg", "png", "mp4", "pdf", "txt", "csv"])
    elif choix_source == "📷 Caméra web":
        media_file = st.camera_input("Prendre une photo")

    # --- GESTION DES SESSIONS ---
    st.markdown("---")
    st.markdown("### 💬 Sessions Enregistrées")
    sessions_enregistrees = db_manager.get_all_sessions()

    for s_id, s_name in sessions_enregistrees:
        is_active = s_id == st.session_state.session_id
        col_btn, col_rename, col_del = st.columns([0.65, 0.17, 0.17])

        with col_btn:
            prefix = "📌 " if is_active else ""
            if st.button(f"{prefix}{s_name}", key=f"sel_{s_id}", use_container_width=True):
                if not is_active:
                    st.session_state.session_id = s_id
                    st.rerun()

        with col_rename:
            if st.button("✏️", key=f"ren_{s_id}"):
                st.session_state[f"editing_{s_id}"] = True

        with col_del:
            if st.button("🗑️", key=f"del_{s_id}"):
                db_manager.delete_session(s_id)
                if is_active:
                    st.session_state.session_id = str(uuid.uuid4())[:8]
                st.rerun()

        if st.session_state.get(f"editing_{s_id}", False):
            nouveau_nom = st.text_input("Nom :", value=s_name, key=f"input_ren_{s_id}")
            if st.button("Valider", key=f"val_{s_id}"):
                if nouveau_nom:
                    db_manager.rename_session(s_id, nouveau_nom)
                    st.session_state[f"editing_{s_id}"] = False
                    st.rerun()

    # --- TÉLÉMÉTRIE EN BAS DE LA SIDEBAR ---
    st.markdown(
        """
        <div class="telemetry-box">
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                <span>Mémoire :</span> <span style="color:#00ff80; font-weight:bold;">Synchronisée</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span>Edge Agent :</span> <span style="color:#00f2fe; font-weight:bold;">Prêt</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- HEADER PRINCIPAL DE COMMAND CENTER ---
st.markdown(
    f"""
    <div style="display: flex; align-items: center; justify-content: space-between; padding-bottom: 16px; border-bottom: 1px solid rgba(0, 242, 254, 0.2); margin-bottom: 24px;">
        <div>
            <h2 style="margin:0; font-size: 1.6rem; color: #ffffff !important; font-weight: 700;">Leyla Core OS</h2>
            <p style="margin:4px 0 0 0; font-size: 0.9rem; color: #00f2fe !important;">Command Center & Edge Agent — Connecté pour <b>Mon Professeur {user_name}</b></p>
        </div>
        <div style="padding: 6px 14px; border-radius: 20px; background: rgba(0, 242, 254, 0.15); border: 1px solid #00f2fe; color: #ffffff; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; font-weight: 600;">
            MODE SÉCURISÉ EDGE
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- AFFICHAGE DE L'HISTORIQUE DES MESSAGES ---
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

# --- BARRE DE CONTRÔLES VOCAUX ---
col_v1, col_v2, col_v3, _ = st.columns([1, 1, 1, 5])
with col_v1:
    btn_parler = st.button("🎙️ Micro", help="Dictée vocale (Micro)")
with col_v2:
    btn_stop = st.button("⏹️ Stop", help="Arrêter la parole")
with col_v3:
    if st.button("🧠 Synchro", help="Synchroniser la mémoire"):
        utils_memoire.extraire_et_sauvegarder_faits(messages)
        st.toast("Mémoire de Leyla synchronisée !")

if btn_stop:
    components.html("""<script>window.parent.window.speechSynthesis.cancel();</script>""", height=0)

if btn_parler:
    components.html(
        """
        <script>
            var recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'fr-FR';
            recognition.onresult = function(event) {
                var text = event.results[0][0].transcript;
                var chatInput = window.parent.document.querySelector('textarea[aria-label="Ordonnez, Mon Professeur..."]');
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

# --- SAISIE ET EXÉCUTION DE L'AGENT ---
prompt_saisi = st.chat_input("Ordonnez, Mon Professeur...")
if prompt_saisi:
    st.session_state.message_en_cours = prompt_saisi

if st.session_state.message_en_cours:
    texte_final = st.session_state.message_en_cours
    st.session_state.message_en_cours = ""

    with st.chat_message("user"):
        st.write(texte_final)
    db_manager.save_message(st.session_state.session_id, "user", texte_final)

    with st.chat_message("assistant"):
        historique_actuel = db_manager.get_history(st.session_state.session_id)

        # Injection dynamique de l'inventaire réseau
        if st.session_state.inventaire_reseau:
            contexte_reseau_str = f"[INVENTAIRE RÉSEAU ACTUEL: {st.session_state.inventaire_reseau}]"
            historique_actuel.append({"role": "system", "content": contexte_reseau_str})
        
        resultat_ia = rechercher_sur_le_web(historique_actuel, image_file=media_file)

        reponse_texte = resultat_ia.get("texte", "...")
        reponse_image_path = resultat_ia.get("image_path")

        st.write(reponse_texte)

        contenu_a_sauvegarder = reponse_texte
        if reponse_image_path and os.path.exists(reponse_image_path):
            st.image(reponse_image_path, caption="Création de Leyla", use_container_width=True)
            contenu_a_sauvegarder += f" [IMAGE:{reponse_image_path}]"

        db_manager.save_message(st.session_state.session_id, "assistant", contenu_a_sauvegarder)

        utils_memoire.extraire_et_sauvegarder_faits(db_manager.get_history(st.session_state.session_id))

        if activer_voix:
            texte_vocale = re.sub(r"[\*\#\_\`\~]", "", reponse_texte)
            texte_vocale = re.sub(r"[\n\r]+", " ", texte_vocale).replace('"', '\\"').replace("'", "\\'")
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
