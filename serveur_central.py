from typing import Optional
import streamlit as st
import pandas as pd
import json
from supabase import create_client, Client
import google.generativeai as genai

# ==========================================
# 0. CONFIGURATION DE LA PAGE STREAMLIT
# ==========================================
st.set_page_config(
    page_title="L.E.Y.L.A. - Serveur Central Multimodaux",
    page_icon="🌐",
    layout="wide"
)

# Configuration de l'API Gemini pour Leïla (si la clé existe dans st.secrets)
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
    except Exception:
        pass

# Import sécurisé du satellite (recherche_ia.py)
try:
    from recherche_ia import rechercher_sur_le_web
except ImportError:
    def rechercher_sur_le_web(historique):
        return {"texte": "Module satellite indisponible temporairement, Mon Professeur."}

# ==========================================
# 1. DÉFINITION DES CODES D'ACTIVATION & STRUCTURES
# ==========================================
# Vous pourrez modifier ou étendre ce dictionnaire selon vos coopératives
STRUCTURES_AUTORISEES = {
    "SOC-2026": {"nom": "Coopérative SOCOAMO", "code_db": "SOCOAMO", "type": "COOP"},
    "NEC-2026": {"nom": "Coopérative NECAB", "code_db": "NECAB", "type": "COOP"},
    "TIA-2026": {"nom": "Coopérative TIASSALÉ", "code_db": "TIASSALE", "type": "COOP"},
    "SOU-2026": {"nom": "Coopérative SOUBRÉ", "code_db": "SOUBRE", "type": "COOP"},
    "LAK-2026": {"nom": "Coopérative LAKOTA", "code_db": "LAKOTA", "type": "COOP"},
    "AGRI-SUPER": {"nom": "Cabinet AGRIFORCE (Direction)", "code_db": "ALL", "type": "ADMIN"}
}

# ==========================================
# 2. GESTION DE LA SESSION & AUTHENTIFICATION
# ==========================================
if "structure_active" not in st.session_state:
    st.session_state["structure_active"] = None

if not st.session_state["structure_active"]:
    st.title("🔐 Access Control - Serveur Central L.E.Y.L.A.")
    st.markdown("##### Veuillez saisir votre code d'activation de structure pour déverrouiller votre espace.")
    
    col_auth1, col_auth2 = st.columns([2, 1])
    with col_auth1:
        code_saisi = st.text_input("Code d'activation unique :", type="password", placeholder="Ex: SOC-2026")
        if st.button("🔓 Activer l'Espace de Travail", type="primary"):
            if code_saisi in STRUCTURES_AUTORISEES:
                st.session_state["structure_active"] = STRUCTURES_AUTORISEES[code_saisi]
                st.success(f"Bienvenue ! Espace initialisé pour : {STRUCTURES_AUTORISEES[code_saisi]['nom']}")
                st.rerun()
            else:
                st.error("Code d'activation invalide. Veuillez vérifier auprès du Cabinet AGRIFORCE.")
    st.stop()

# Structure actuellement connectée
structure_courante = st.session_state["structure_active"]

# ==========================================
# 3. CONNEXION ET FILTRAGE SUPABASE
# ==========================================
@st.cache_resource
def init_supabase() -> Optional[Client]:
    """Initialise le client Supabase à partir des secrets Streamlit."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erreur de configuration des secrets Supabase : {e}")
        return None

supabase = init_supabase()

def charger_donnees_isolees(module_choisi: str, code_structure_filtre: str) -> pd.DataFrame:
    """
    Récupère la table unique Supabase avec double filtrage :
    1. Filtrage étanche par Structure / Coopérative
    2. Filtrage strict par Module fonctionnel
    """
    if not supabase:
        return pd.DataFrame()
    try:
        query = supabase.table("producteurs_parcelles").select("*")
        
        # SÉCURITÉ : Si la structure n'est pas le Cabinet AGRIFORCE (ALL), on filtre strictement par coopérative
        if code_structure_filtre != "ALL":
            query = query.eq("code_cooperative", code_structure_filtre)
            
        response = query.execute()
        data = response.data
        
        if data:
            df_global = pd.DataFrame(data)
            
            if "module_execute" in df_global.columns:
                if "Géolocalisation" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Géo", case=False, na=False)].reset_index(drop=True)
                elif "Diagnostic" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Diagnostic", case=False, na=False)].reset_index(drop=True)
                elif "Rendement" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Rendement", case=False, na=False)].reset_index(drop=True)
                elif "PDC" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("PDC|Développement", case=False, na=False)].reset_index(drop=True)
            
            return df_global
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données Supabase : {e}")
        return pd.DataFrame()

# ==========================================
# 4. MOTEUR D'ANALYSE DECISIONNELLE LEÏLA (PDC)
# ==========================================
def leila_analyse_pdc_metier(donnees_producteur: dict):
    """
    Module d'analyse décisionnelle multidimensionnelle Leïla (PDC).
    """
    nom = donnees_producteur.get("nom_producteur", "Inconnu")
    code = donnees_producteur.get("code_producteur", "N/A")
    superficie = float(donnees_producteur.get("superficie", 0.0) or 0.0)
    age_parcelle = int(donnees_producteur.get("age_cacaoyere", 0) or 0)
    
    # Extraire les objets JSON / dictionnaires enregistrés
    reponses = donnees_producteur.get("reponses_pdc", {})
    if isinstance(reponses, str):
        try:
            reponses = json.loads(reponses)
        except Exception:
            reponses = {}

    st.markdown(f"### 🤖 Diagnostic de Leïla pour le PDC : **{nom}** (`{code}`)")
    
    score_sante = reponses.get("score_pression_sanitaire", 0)
    solde_net = reponses.get("solde_net_estime", 0)
    toposequence = reponses.get("toposequence", "Non spécifiée")
    tendance = reponses.get("tendance_production_3ans_pct", 0)
    part_cacao = reponses.get("part_revenu_cacao_pct", 100)
    production_annuelle = reponses.get("production_annuelle_kg", 0)
    arbres_ombrage_ha = reponses.get("arbres_ombrage_ha", 0)

    rendement_ha = (production_annuelle / superficie) if superficie > 0 else 0

    tab1, tab2, tab3, tab4 = st.tabs([
        "🌱 Agronomie & Rendement", 
        "💰 Économie & Foyer", 
        "🌳 Durabilité & RDUE", 
        "🧠 Synthèse IA Leïla"
    ])

    with tab1:
        st.subheader("Diagnostic Agronomique")
        c1, c2, c3 = st.columns(3)
        c1.metric("Superficie", f"{superficie:.2f} ha")
        c2.metric("Rendement Estimé", f"{rendement_ha:.0f} kg/ha")
        c3.metric("Âge du Verger", f"{age_parcelle} ans")

        if score_sante <= 3:
            st.success("• **Pression sanitaire faible :** Verger sain et bien entretenu.")
        elif score_sante <= 7:
            st.warning("• **Pression sanitaire modérée :** Risques identifiés (gourmands, ombrage excessif).")
        else:
            st.error("• **Pression sanitaire critique :** Traitement d'urgence et taille requis.")

        if toposequence in ["Bas-fond", "Bas de versant"]:
            st.warning(f"• **Risque Toposéquence ({toposequence}) :** Vigilance risque d'asphyxie racinaire.")

    with tab2:
        st.subheader("Bilan Économique")
        col_e1, col_e2, col_e3 = st.columns(3)
        col_e1.metric("Solde Net Estimé", f"{solde_net:,.0f} FCFA")
        col_e2.metric("Évolution Prod. (3 ans)", f"{tendance:+.1f}%")
        col_e3.metric("Part Revenu Cacao", f"{part_cacao:.1f}%")

        if part_cacao > 85:
            st.warning("• **Dépendance forte au cacao :** Proposer une diversification (cultures vivrières).")

    with tab3:
        st.subheader("Conformité Environnementale & Agroforesterie")
        if arbres_ombrage_ha >= 18:
            st.success(f"• **Taux d'ombrage conforme RDUE :** {arbres_ombrage_ha} arbres/ha.")
        else:
            st.error(f"• **Déficit d'arbres d'ombrage :** {arbres_ombrage_ha} arbres/ha (Objectif: >=18/ha).")

    with tab4:
        st.subheader("📝 Analyse Narrative Rédigée par Leïla (Gemini)")
        if st.button("✨ Déclencher l'Analyse Narrative de Leïla", type="primary"):
            if GEMINI_KEY:
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    prompt = f"""
                    Tu es Leïla, conseillère agronomique senior chez AGRIFORCE.
                    Rédige un diagnostic synthétique et concret pour ce PDC :
                    - Producteur : {nom} (Code: {code})
                    - Superficie : {superficie} ha | Âge : {age_parcelle} ans
                    - Rendement : {rendement_ha:.1f} kg/ha | Production : {production_annuelle} kg
                    - Solde Net : {solde_net} FCFA | Dépendance Cacao : {part_cacao}%
                    - Score Sanitaire : {score_sante}/10 | Arbres/ha : {arbres_ombrage_ha}

                    Structure ton analyse :
                    1. Diagnostic des forces et vulnérabilités de l'exploitation.
                    2. Plan d'intervention prioritaire en 3 actions pour le conseiller.
                    3. Recommandation d'accompagnement financier/social.
                    """
                    with st.spinner("Leïla analyse le PDC et rédige le rapport..."):
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
                except Exception as e:
                    st.error(f"Erreur lors de la génération de l'analyse narrative : {e}")
            else:
                st.info("💡 La clé `GEMINI_API_KEY` doit être configurée dans vos Secrets Streamlit pour activer l'analyse narrative.")

# ==========================================
# 5. NAVIGATION & BARRE LATÉRALE
# ==========================================
st.sidebar.title(f"🏢 {structure_courante['nom']}")
if st.sidebar.button("🚪 Déconnexion / Changer de Code"):
    st.session_state["structure_active"] = None
    st.rerun()

st.sidebar.divider()

# Gestion du filtrage Super-Admin Cabinet AGRIFORCE
code_filtre_db = structure_courante["code_db"]
if structure_courante["type"] == "ADMIN":
    st.sidebar.header("👁️ Vue Supervision AGRIFORCE")
    choix_coop_admin = st.sidebar.selectbox(
        "Filtrer par Coopérative :",
        ["Toutes les coopératives (Global)", "SOCOAMO", "NECAB", "TIASSALE", "SOUBRE", "LAKOTA"]
    )
    if choix_coop_admin != "Toutes les coopératives (Global)":
        code_filtre_db = choix_coop_admin

st.sidebar.header("🎛️ Sélection du Module")
module_choisi = st.sidebar.selectbox(
    "Choisir le domaine d'analyse",
    [
        "Géolocalisation & RDUE (Parcelles)",
        "Diagnostic Phytosanitaire",
        "Estimation de Rendement",
        "Plan de Développement (PDC)"
    ]
)

# ==========================================
# 6. APPLICATION PRINCIPALE & TABLEAUX
# ==========================================
st.title("🌐 L.E.Y.L.A. - Centre de Commandement Global")
st.caption(f"Connecté en tant que : **{structure_courante['nom']}** | Filtre actif : `{code_filtre_db}`")

# Chargement étanche des données
df_filtered = charger_donnees_isolees(module_choisi, code_filtre_db)

st.subheader(f"📊 Module actif : {module_choisi}")

with st.expander(f"📁 Afficher / Masquer les données ({len(df_filtered)} enregistrement(s))", expanded=False):
    if not df_filtered.empty:
        st.dataframe(df_filtered, use_container_width=True)
    else:
        st.info(f"Aucune donnée enregistrée pour le module : {module_choisi}.")

st.divider()

# ==========================================
# 7. MODULE PDC & ANALYSE PAR PRODUCTEUR
# ==========================================
if "PDC" in module_choisi:
    st.subheader("🔍 Consultation Approfondie d'un PDC Synchronisé")
    
    if not df_filtered.empty:
        col_nom = "nom_producteur" if "nom_producteur" in df_filtered.columns else df_filtered.columns[0]
        liste_producteurs = df_filtered[col_nom].unique().tolist()
        
        producteur_selectionne = st.selectbox("Sélectionner un producteur :", liste_producteurs)
        
        if st.button("Consulter le PDC avec Leïla 🤖", type="primary"):
            ligne_prod = df_filtered[df_filtered[col_nom] == producteur_selectionne].iloc[0].to_dict()
            leila_analyse_pdc_metier(ligne_prod)
    else:
        st.warning("Aucun PDC disponible pour cette sélection.")

    st.divider()

# ==========================================
# 8. SATELLITE IA (HUB UNIVERSEL)
# ==========================================
st.subheader("🤖 Assistant IA L.E.Y.L.A. (Analyse Experte Ciblée)")
user_query = st.text_input("Posez une question sur les données du module actif :")

if st.button("Lancer l'analyse du satellite"):
    if not user_query:
        st.warning("Veuillez saisir une question.")
    else:
        with st.spinner("Analyse en cours par Leïla..."):
            try:
                contexte_donnees = df_filtered.to_string(index=False) if not df_filtered.empty else "Aucune donnée."
                prompt_complet = (
                    f"Tu es L.E.Y.L.A., l'IA centrale du cabinet AGRIFORCE.\n"
                    f"Structure active : {structure_courante['nom']}\n"
                    f"Module : {module_choisi}\n"
                    f"Données du module :\n{contexte_donnees}\n\n"
                    f"Question : {user_query}"
                )
                historique = [{"role": "user", "content": prompt_complet}]
                reponse_satellite = rechercher_sur_le_web(historique)
                st.success("Réponse du Satellite L.E.Y.L.A. :")
                st.write(reponse_satellite.get("texte", ""))
            except Exception as e:
                st.error(f"Erreur de communication : {e}")
