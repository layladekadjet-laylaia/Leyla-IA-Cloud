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

# --- CSS SUR MESURE : THÈME BLEU CIEL LUMINEUX ET TEXTE NET ---
st.markdown(
    f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', sans-serif;
    }}

    /* Fond principal bleu ciel très doux */
    .stApp {{
        background: #e0f2fe !important;
        color: #0f172a !important;
    }}

    /* Filigrane central discret */
    .stApp::before {{
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 380px;
        height: 380px;
        background-image: url("data:image/png;base64,{img_base64}");
        background-repeat: no-repeat;
        background-size: contain;
        opacity: 0.06;
        pointer-events: none;
        z-index: 0;
    }}

    /* Panneau latéral (Sidebar) Bleu ciel épuré */
    [data-testid="stSidebar"] {{
        background: #bae6fd !important;
        border-right: 1px solid #7dd3fc !important;
    }}

    [data-testid="stSidebar"] * {{
        color: #0369a1 !important;
    }}

    /* Titres & typographies nettes */
    h1, h2, h3, h4, p, label {{
        color: #0f172a !important;
        font-weight: 600;
    }}

    /* Cartes de messages style blanc/verre lumineuse */
    [data-testid="stChatMessage"] {{
        background: rgba(255, 255, 255, 0.85) !important;
        backdrop-filter: blur(10px);
        border: 1px solid #38bdf8 !important;
        border-radius: 16px !important;
        padding: 1.2rem !important;
        box-shadow: 0 4px 20px rgba(14, 165, 233, 0.15) !important;
        margin-bottom: 1rem !important;
        color: #0f172a !important;
    }}

    /* Boutons en bleu vif avec texte noir/sombre net */
    div.stButton > button {{
        background: #ffffff !important;
        border: 1px solid #38bdf8 !important;
        color: #0369a1 !important;
        border-radius: 10px !important;
        transition: all 0.2s ease-in-out !important;
        font-weight: 600 !important;
    }}

    div.stButton > button:hover {{
        background: #0284c7 !important;
        border-color: #0284c7 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3) !important;
        transform: translateY(-1px);
    }}

    /* Zone d'entrée de chat : Fond blanc, ÉCRITURE EN NOIR INTENSE */
    [data-testid="stChatInput"] {{
        background: #ffffff !important;
        border-radius: 12px !important;
        border: 2px solid #0284c7 !important;
        box-shadow: 0 4px 20px rgba(2, 132, 199, 0.2) !important;
    }}

    [data-testid="stChatInput"] textarea {{
        color: #000000 !important;
        font-weight: 600 !important;
    }}

    [data-testid="stChatInput"] textarea::placeholder {{
        color: #64748b !important;
        font-weight: 400 !important;
    }}

    /* Card utilisateur sidebar */
    .user-card {{
        padding: 10px 14px;
        border-radius: 8px;
        background: #ffffff;
        border: 1px solid #38bdf8;
        color: #0284c7 !important;
        font-size: 0.875rem;
        font-weight: 700;
    }}

    .telemetry-box {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #0369a1;
        border-top: 1px solid #7dd3fc;
        padding-top: 12px;
        margin-top: 20px;
    }}

    .indicator-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #0284c7;
        box-shadow: 0 0 10px #0284c7;
        display: inline-block;
    }}
</style>
""",
    unsafe_allow_html=True,
)

# --- IMPORTATION DES MODULES OPTIONNELS ---
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
                <h1 style="margin: 0; font-size: 2rem; color: #0284c7 !important;">LEYLA v2.6</h1>
                <p style="color: #334155; font-size: 0.9rem; margin-top: 6px;">Initialisation de l'Agent Edge</p>
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

# --- BARRE LATÉRALE (SIDEBAR BLEU CIEL) ---
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 24px;">
            <div class="indicator-dot"></div>
            <h1 style="font-size: 1.125rem; margin: 0; color: #0284c7 !important; font-weight: 700;">
                LEYLA <span style="font-size: 0.75rem; color: #0369a1; font-weight: 500;">v2.6</span>
            </h1>
        </div>
        <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #0369a1; font-family: 'JetBrains Mono', monospace; margin-bottom: 6px;">
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
    st.markdown("<p style='font-size: 0.85rem; font-weight: 700; color: #0369a1;'>👑 Fonctions LEYLA</p>", unsafe_allow_html=True)

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
    st.markdown("<p style='font-size: 0.85rem; font-weight: 700; color: #0369a1;'>📱 Découverte Réseau & IoT</p>", unsafe_allow_html=True)

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
    st.markdown("<p style='font-size: 0.85rem; font-weight: 700; color: #0369a1;'>🎨 Studio Multimédia</p>", unsafe_allow_html=True)
    choix_source = st.radio("Source média :", ["Aucune", "📁 Fichier", "📷 Caméra web"])

    media_file = None
    if choix_source == "📁 Fichier":
        media_file = st.file_uploader("Fichier", type=["jpg", "jpeg", "png", "mp4", "pdf", "txt", "csv"])
    elif choix_source == "📷 Caméra web":
        media_file = st.camera_input("Prendre une photo")

    # --- GESTION DES SESSIONS ---
    st.markdown("---")
    st.markdown("<p style='font-size: 0.85rem; font-weight: 700; color: #0369a1;'>💬 Sessions Enregistrées</p>", unsafe_allow_html=True)
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
                <span>Mémoire :</span> <span style="color:#0284c7; font-weight:bold;">Synchronisée</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span>Edge Agent :</span> <span style="color:#16a34a; font-weight:bold;">Prêt</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- HEADER PRINCIPAL LUMINEUX ---
st.markdown(
    f"""
    <div style="display: flex; align-items: center; justify-content: space-between; padding-bottom: 16px; border-bottom: 2px solid #7dd3fc; margin-bottom: 24px;">
        <div>
            <h2 style="margin:0; font-size: 1.6rem; color: #0284c7 !important; font-weight: 800;">Leyla Core OS</h2>
            <p style="margin:2px 0 0 0; font-size: 0.9rem; color: #334155;">Command Center & Edge Agent — Connecté pour Mon Professeur <b>{user_name}</b></p>
        </div>
        <div style="padding: 6px 14px; border-radius: 20px; background: #ffffff; border: 1px solid #0284c7; color: #0284c7; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; font-weight: 700;">
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
