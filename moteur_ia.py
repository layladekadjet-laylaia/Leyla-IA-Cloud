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
    page_title="Leyla IA - Edge Agent", 
    page_icon="🤖", 
    layout="wide", # Mode large pour un effet tableau de bord spectaculaire
    initial_sidebar_state="expanded"
)

# --- CHARGEMENT DU LOGO EN BASE64 ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

img_base64 = get_base64_image("LOGO LAYLA.png")

# --- DESIGN SYSTEM & CSS ULTRA-CAPTIVANT (GLASSMORPHISM & NÉON) ---
st.markdown(
    f"""
<style>
    /* Importation d'une police moderne (Inter / Orbitron vibe) */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', sans-serif;
    }}

    /* Fond principal sombre et immersif */
    .stApp {{
        background: radial-gradient(circle at 50% 10%, #0d1117 0%, #05070a 100%);
        color: #e6edf3;
    }}

    /* Filigrane central sophistiqué */
    .stApp::before {{
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 450px;
        height: 450px;
        background-image: url("data:image/png;base64,{img_base64}");
        background-repeat: no-repeat;
        background-size: contain;
        opacity: 0.04;
        pointer-events: none;
        z-index: 0;
        filter: drop-shadow(0 0 50px rgba(0, 242, 254, 0.2));
    }}

    /* Sidebar futuriste en verre poli */
    [data-testid="stSidebar"] {{
        background: rgba(13, 17, 23, 0.85);
        backdrop-filter: blur(16px);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }}

    /* Cartes et conteneurs effet verre */
    div.stButton > button {{
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #e6edf3;
        border-radius: 12px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        font-weight: 500;
    }}

    div.stButton > button:hover {{
        background: linear-gradient(135deg, rgba(0, 242, 254, 0.15) 0%, rgba(79, 172, 254, 0.1) 100%);
        border-color: #00f2fe;
        color: #00f2fe;
        box-shadow: 0 0 20px rgba(0, 242, 254, 0.3);
        transform: translateY(-2px);
    }}

    /* Bulles de chat personnalisées */
    [data-testid="stChatMessage"] {{
        background: rgba(22, 27, 34, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 16px;
        padding: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        margin-bottom: 1rem;
    }}

    /* Zone de saisie flottante high-tech */
    [data-testid="stChatInput"] {{
        background: rgba(13, 17, 23, 0.9);
        border-radius: 16px;
        border: 1px solid rgba(0, 242, 254, 0.3);
        box-shadow: 0 0 25px rgba(0, 242, 254, 0.1);
    }}

    /* Titres avec lueur élégante */
    h1, h2, h3 {{
        color: #ffffff;
        font-weight: 700;
        letter-spacing: -0.5px;
    }}

    /* Badges et statuts lumineux */
    .status-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        background: rgba(0, 255, 128, 0.1);
        border: 1px solid rgba(0, 255, 128, 0.3);
        color: #00ff80;
        font-size: 0.8rem;
        font-weight: 600;
        box-shadow: 0 0 10px rgba(0, 255, 128, 0.2);
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
    col1, col2, col1 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🤖 Bienvenue sur Leyla OS</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #8b949e;'>Votre Agent Edge Autonome et Sécurisé</p>", unsafe_allow_html=True)
        nom_saisi = st.text_input("Comment dois-je vous appeler, Mon Professeur ?", placeholder="Entrez votre nom...")
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

# --- BARRE LATÉRALE (SIDEBAR - CONTRÔLEUR LEYLA) ---
with st.sidebar:
    st.markdown("### ⚡ LEYLA // COMMAND")
    st.markdown('<span class="status-badge">● SYSTÈME ACTIF</span>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("➕ Nouvelle Discussion", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.rerun()

    activer_voix = st.checkbox("🔊 Réponse vocale automatique", value=True)

    # --- FONCTIONNALITÉS JARVIS ---
    st.markdown("---")
    st.markdown("### 👑 Modules Exécutifs")

    if st.button("🎧 Écoute Passive (Wake Word)", use_container_width=True):
        st.toast("Pour activer l'écoute passive, utilisez le script mobile dédié.")

    if st.button("🌅 Briefing Matinal Proactif", use_container_width=True):
        if generer_briefing_matinal:
            with st.spinner("Génération de votre briefing, Mon Professeur..."):
                briefing = generer_briefing_matinal()
                st.session_state.message_en_cours = briefing
                st.rerun()
        else:
            st.error("Module briefing_leyla.py introuvable.")

    if st.button("🧠 Synchro Mémoire Long Terme", use_container_width=True):
        messages = db_manager.get_history(st.session_state.session_id)
        utils_memoire.extraire_et_sauvegarder_faits(messages)
        st.toast("Mémoire de Leyla synchronisée !")

    # --- DÉCOUVERTE MATÉRIELLE AUTOMATIQUE ---
    st.markdown("---")
    st.markdown("### 📱 Scanner & IoT Réseau")

    type_recherche = st.selectbox(
        "Cible de recherche :", ["Bluetooth Proche", "Passerelle & Appareils Wi-Fi (IoT/Caméras)"]
    )

    if st.button("🔍 Lancer le Scan Global", use_container_width=True):
        if type_recherche == "Bluetooth Proche":
            with st.spinner("Leyla analyse les ondes Bluetooth..."):
                appareils_bt = asyncio.run(utils_scan.scanner_bluetooth_proche())
                if appareils_bt:
                    st.success(f"{len(appareils_bt)} appareil(s) Bluetooth détecté(s)")
                    for dev in appareils_bt:
                        st.info(f"📱 **{dev['nom']}**\n- Adresse : `{dev['adresse']}`")
                else:
                    st.warning("Aucun appareil Bluetooth détecté.")
        else:
            with st.spinner("Cartographie complète du réseau en cours..."):
                rapport = utils_scan.scanner_reseau_complet()
                st.session_state.inventaire_reseau = rapport['appareils']
                infos_routeur = utils_scan.interroger_interface_routeur(rapport['passerelle'])
                
                st.success(f"Passerelle : `{rapport['passerelle']}` | {rapport['total_appareils']} actif(s)")
                if infos_routeur['accessible']:
                    st.info(f"🌐 **Routeur Web** : {infos_routeur['titre_page']}")
                else:
                    st.warning(f"🌐 Routeur Web : {infos_routeur['message']}")

    # --- COFFRE-FORT SÉCURISÉ ---
    st.markdown("---")
    st.markdown("### 🔐 Coffre-fort Caméras")
    with st.expander("Configurer les accès IP"):
        ip_cible_cred = st.text_input("Adresse IP", placeholder="192.168.100.50")
        user_cred = st.text_input("Utilisateur", value="admin")
        pass_cred = st.text_input("Mot de passe", type="password")
        if st.button("Enregistrer", use_container_width=True):
            if ip_cible_cred:
                db_manager.save_device_credentials(ip_cible_cred, user_cred, pass_cred)
                st.toast("Accès enregistrés !")

    # --- SECTION MULTIMÉDIA ---
    st.markdown("---")
    st.markdown("### 🎨 Studio Multimédia")
    choix_source = st.radio(
        "Source média :",
        ["Aucune", "📁 Fichier", "📷 Caméra web"],
        horizontal=False,
    )

    media_file = None
    if choix_source == "📁 Fichier":
        media_file = st.file_uploader("Fichier", type=["jpg", "jpeg", "png", "mp4", "pdf", "txt"])
    elif choix_source == "📷 Caméra web":
        media_file = st.camera_input("Prendre une photo")

    # --- GESTION DES SESSIONS ---
    st.markdown("---")
    st.markdown("### 💬 Historique Sessions")
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
            if st.button("OK", key=f"val_{s_id}"):
                if nouveau_nom:
                    db_manager.rename_session(s_id, nouveau_nom)
                    st.session_state[f"editing_{s_id}"] = False
                    st.rerun()

# --- HEADER PRINCIPAL ---
st.markdown(
    f"""
    <div style='display: flex; align-items: center; justify-content: space-between; padding-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 20px;'>
        <div>
            <h2 style='margin: 0; background: linear-gradient(90deg, #00f2fe, #4facfe); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>Leyla Core OS</h2>
            <p style='margin: 0; color: #8b949e; font-size: 0.9rem;'>Command Center & Edge Agent - Connecté pour {user_name}</p>
        </div>
        <div>
            <span class='status-badge'>MODE SECOURISÉ EDGE</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

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
col_v1, col_v2, col_v3, col_v4 = st.columns([1, 1, 1, 6])
with col_v1:
    btn_parler = st.button("🎙️ Micro", help="Dictée vocale")
with col_v2:
    btn_stop = st.button("⏹️ Stop", help="Arrêter la parole")
with col_v3:
    btn_sync = st.button("🧠 Synchro", help="Mettre à jour la mémoire")

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
prompt_saisi = st.chat_input("Commandez Leyla ou posez votre question...")
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

        if st.session_state.inventaire_reseau:
            contexte_reseau_str = f"[INVENTAIRE RÉSEAU ACTUEL: {st.session_state.inventaire_reseau}]"
            historique_actuel.append({"role": "system", "content": contexte_reseau_str})
        
        resultat_ia = rechercher_sur_le_web(historique_actuel, image_file=media_file)

        reponse_texte = resultat_ia.get("texte", "...")
        reponse_image_path = resultat_ia.get("image_path")

        st.write(reponse_texte)

        contenu_a_sauvegarder = reponse_texte
        if reponse_image_path and os.path.exists(reponse_image_path):
            st.image(reponse_image_path, caption="Création visuelle par Leyla", use_container_width=True)
            contenu_a_sauvegarder += f" [IMAGE:{reponse_image_path}]"

        db_manager.save_number = db_manager.save_message(st.session_state.session_id, "assistant", contenu_a_sauvegarder)
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
