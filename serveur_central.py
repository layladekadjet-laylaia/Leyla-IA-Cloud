from typing import Optional
import streamlit as st
import pandas as pd
import json
from supabase import create_client, Client

# ==========================================
# 0. CONFIGURATION DE LA PAGE STREAMLIT
# ==========================================
st.set_page_config(
    page_title="L.E.Y.L.A. - Serveur Central Multimodaux",
    page_icon="🌐",
    layout="wide"
)

# Import sécurisé du satellite (recherche_ia.py)
try:
    from recherche_ia import rechercher_sur_le_web
except ImportError:
    def rechercher_sur_le_web(historique):
        return {"texte": "Module satellite indisponible temporairement, Mon Professeur."}

# ==========================================
# 0.B SYSTEME D'ACTIVATION ET CODES COOPÉRATIVES
# ==========================================
STRUCTURES_AUTORISEES = {
    "SOC-2026": {"nom": "Coopérative SOCOAMO", "code_db": "SOCOAMO", "type": "COOP"},
    "NEC-2026": {"nom": "Coopérative NECAB", "code_db": "NECAB", "type": "COOP"},
    "TIA-2026": {"nom": "Coopérative TIASSALÉ", "code_db": "TIASSALE", "type": "COOP"},
    "SOU-2026": {"nom": "Coopérative SOUBRÉ", "code_db": "SOUBRE", "type": "COOP"},
    "LAK-2026": {"nom": "Coopérative LAKOTA", "code_db": "LAKOTA", "type": "COOP"},
    "AGRI-SUPER": {"nom": "Cabinet AGRIFORCE (Direction)", "code_db": "ALL", "type": "ADMIN"}
}

if "structure_active" not in st.session_state:
    st.session_state["structure_active"] = None

# Écran de verrouillage si aucun code valide n'est saisi
if not st.session_state["structure_active"]:
    st.title("🔐 Authentification - Serveur Central L.E.Y.L.A.")
    st.markdown("##### Entrez le code d'activation attribué à votre structure pour accéder aux données.")
    
    col_code, col_btn = st.columns([2, 1])
    with col_code:
        code_saisi = st.text_input("Code d'accès structure :", type="password", placeholder="Ex: SOC-2026")
    with col_btn:
        st.write("")
        st.write("")
        if st.button("🔓 Déverrouiller L.E.Y.L.A.", type="primary"):
            if code_saisi in STRUCTURES_AUTORISEES:
                st.session_state["structure_active"] = STRUCTURES_AUTORISEES[code_saisi]
                st.success(f"Accès autorisé : {STRUCTURES_AUTORISEES[code_saisi]['nom']}")
                st.rerun()
            else:
                st.error("Code invalide. Veuillez contacter le Cabinet AGRIFORCE.")
    st.stop()

structure_courante = st.session_state["structure_active"]

# ==========================================
# 1. CONNEXION À SUPABASE (CLOUD)
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
    """Récupère la table unique Supabase et isole strictement les données selon la coopérative et le module."""
    if not supabase:
        return pd.DataFrame()
    try:
        # Récupération globale pour éviter l'erreur de colonne manquante
        response = supabase.table("producteurs_parcelles").select("*").execute()
        data = response.data
        if data:
            df_global = pd.DataFrame(data)
            
            # 1. Filtre par coopérative (si la colonne existe dans vos données)
            if code_structure_filtre != "ALL" and "code_cooperative" in df_global.columns:
                df_global = df_global[df_global["code_cooperative"] == code_structure_filtre]
            
            # 2. Filtrage strict par module actif
            if "module_execute" in df_global.columns:
                if "Géolocalisation" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Géo", case=False, na=False)].reset_index(drop=True)
                elif "Diagnostic" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Diagnostic", case=False, na=False)].reset_index(drop=True)
                elif "Rendement" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Rendement", case=False, na=False)].reset_index(drop=True)
                elif "PDC" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("PDC|Développement", case=False, na=False)].reset_index(drop=True)
            
            return df_global.reset_index(drop=True)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données Supabase : {e}")
        return pd.DataFrame()


# ==========================================
# 2. MOTEUR D'ANALYSE DÉCISIONNELLE LEÏLA (PDC)
# ==========================================
import json
import streamlit as st

def extraire_etapes_pdc(donnees_producteur: dict) -> dict:
    """Décompresse et normalise les 15 étapes du PDC enregistrées depuis la tablette."""
    raw_pdc = donnees_producteur.get("reponses_pdc", {})
    if isinstance(raw_pdc, str):
        try:
            raw_pdc = json.loads(raw_pdc)
        except Exception:
            raw_pdc = {}

    def get_field(key_name, step_name=None, default=None):
        if key_name in raw_pdc:
            return raw_pdc[key_name]
        if step_name and isinstance(raw_pdc.get(step_name), dict):
            return raw_pdc[step_name].get(key_name, default)
        return default

    return {
        "foyer": get_field("taille_foyer", "etape_1_foyer", 1),
        "superficie": get_field("superficie_totale_ha", "etape_2_foncier", 0.0),
        "statut_foncier": get_field("statut_foncier", "etape_2_foncier", "Inconnu"),
        "sante_verger": get_field("score_pression_sanitaire", "etape_4_sante_verger", 0),
        "age_verger": get_field("age_moyen_verger_ans", "etape_4_sante_verger", 0),
        "maladies": get_field("maladies_presentes", "etape_5_pathologies", []),
        "toposequence": get_field("toposequence", "etape_6_toposequence", "Plateau"),
        "materiel": get_field("etat_materiel", "etape_8_equipements", "Moyen"),
        "eau_proche": get_field("point_eau_proche", "etape_9_eau", False),
        "rev_cacao": get_field("revenu_annuel_cacao", "etape_10_revenus_cacao", 0.0),
        "rev_hors_cacao": get_field("revenu_annuel_hors_cacao", "etape_11_autres_revenus", 0.0),
        "chg_ferme": get_field("charges_exploitation_annuelles", "etape_12_charges_ferme", 0.0),
        "chg_foyer": get_field("charges_foyer_annuelles", "etape_13_charges_foyer", 0.0),
        "credit_demande": get_field("montant_credit_demande", "etape_15_besoins_financement", 0.0)
    }


def leila_analyse_pdc_metier(donnees_producteur: dict):
    """Moteur d'Analyse Intégrale Leïla basique sur les 15 étapes transmises."""
    if not isinstance(donnees_producteur, dict):
        st.error("⚠️ Données invalides pour l'analyse.")
        return

    # 1. Extraction propre des 15 étapes
    p = extraire_etapes_pdc(donnees_producteur)
    
    nom = donnees_producteur.get("nom_producteur", "Producteur Inconnu")
    code = donnees_producteur.get("code_producteur", "N/A")

    st.markdown(f"### 🤖 Diagnostic L.E.Y.L.A. pour **{nom}** (`{code}`)")
    st.markdown("---")

    # 2. Bilan Financier
    rev_tot = p["rev_cacao"] + p["rev_hors_cacao"]
    chg_tot = p["chg_ferme"] + p["chg_foyer"]
    solde = rev_tot - chg_tot
    part_cacao = (p["rev_cacao"] / rev_tot * 100) if rev_tot > 0 else 100

    st.markdown("**💰 Bilan Financier du Foyer (FCFA)**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenu Total", f"{rev_tot:,.0f} F")
    c2.metric("Charges Totales", f"{chg_tot:,.0f} F")
    c3.metric("Solde Net Disponible", f"{solde:,.0f} F")
    c4.metric("Part Cacao", f"{part_cacao:.0f}%")

    # 3. Évaluation Agronomique & Sanitaire
    st.markdown("**🌱 Diagnostic Parcelle & Pression Fitosanitaire**")
    if p["sante_verger"] > 6:
        st.error(f"• **Pression Sanitaire Critique ({p['sante_verger']}/10)** : Action corrective immédiate requise.")
    else:
        st.success(f"• **Pression Sanitaire Maîtrisée ({p['sante_verger']}/10)**.")

    if p["toposequence"] in ["Bas-fond", "Bas de versant"] and "Pourriture brune" in p["maladies"]:
        st.error("🔥 **Risque Majeur Phytophthora :** Zone humide + Pourriture brune active. Drainer et traiter.")

    # 4. Plan d'action stratégique
    st.markdown("**💡 Feuille de Route Opérationnelle Recommandée**")
    plan = []

    if solde < 100000:
        plan.append("Orienter vers des intrants subventionnés et formations au compostage (marge financière faible).")
    else:
        plan.append("Capacité financière suffisante : Valider le plan de fertilisation raisonnée.")

    if p["age_verger"] >= 25:
        plan.append("Verger âgé : Programmer un plan de régénération progressive ou de recépage.")

    if p["materiel"] in ["Vétuste", "Inexistant"]:
        plan.append("Dotation prioritaire en petit matériel de taille (scies/podo-coupes).")

    for idx, action in enumerate(plan, 1):
        st.info(f"**Action {idx} :** {action}")


# ==========================================
# 3. INTERFACE DU SERVEUR CENTRAL
# ==========================================
st.title("🌐 L.E.Y.L.A. - Centre de Commandement Global")
st.markdown(f"*Espace de travail connecté : **{structure_courante['nom']}***")

# Barre latérale : Informations structure et Déconnexion
st.sidebar.title(f"🏢 {structure_courante['nom']}")
if st.sidebar.button("🚪 Changer de structure / Déconnexion"):
    st.session_state["structure_active"] = None
    st.rerun()

st.sidebar.divider()

# Gestion du filtrage pour le Cabinet AGRIFORCE
code_filtre_db = structure_courante["code_db"]
if structure_courante["type"] == "ADMIN":
    st.sidebar.header("👁️ Super-Vision AGRIFORCE")
    choix_coop_admin = st.sidebar.selectbox(
        "Sélectionner la vue coopérative :",
        ["Toutes les coopératives", "SOCOAMO", "NECAB", "TIASSALE", "SOUBRE", "LAKOTA"]
    )
    if choix_coop_admin != "Toutes les coopératives":
        code_filtre_db = choix_coop_admin

# Sélection du module dans la barre latérale
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

# Chargement strict des données du module sélectionné et filtrées par la structure
df_filtered = charger_donnees_isolees(module_choisi, code_filtre_db)

st.subheader(f"📊 Module actif : {module_choisi}")

# Affichage du tableau dans un bloc déroulant
with st.expander(f"📁 Afficher / Masquer les données brutes ({len(df_filtered)} enregistrement(s))", expanded=False):
    if not df_filtered.empty:
        st.dataframe(df_filtered, use_container_width=True)
    else:
        st.info(f"Aucune donnée enregistrée pour le module {module_choisi} dans cette structure.")

st.divider()

# ==========================================
# 4. MODULE DÉDIÉ PDC : ANALYSE PAR PRODUCTEUR
# ==========================================
if "PDC" in module_choisi:
    st.subheader("🔍 Consultation Approfondie d'un PDC Synchronisé")
    
    if not df_filtered.empty:
        # Extrait la liste des producteurs synchronisés
        col_nom = "nom_producteur" if "nom_producteur" in df_filtered.columns else df_filtered.columns[0]
        liste_producteurs = df_filtered[col_nom].unique().tolist()
        
        producteur_selectionne = st.selectbox("Sélectionner un producteur synchronisé :", liste_producteurs)
        
        if st.button("Analyser le PDC avec Leïla 🤖", type="primary"):
            ligne_prod = df_filtered[df_filtered[col_nom] == producteur_selectionne].iloc[0].to_dict()
            leila_analyse_pdc_metier(ligne_prod)
    else:
        st.warning("Aucun PDC synchronisé disponible dans la base pour le moment.")

    st.divider()

# ==========================================
# 5. INTERACTION AVEC LE SATELLITE IA (HUB UNIVERSEL)
# ==========================================
st.subheader("🤖 Assistant IA L.E.Y.L.A. (Analyse Experte Ciblée)")
st.markdown(f"Posez vos questions en lien direct avec le module **{module_choisi}**.")

user_query = st.text_input("Votre requête pour le satellite :")

if st.button("Lancer l'analyse du satellite"):
    if not user_query:
        st.warning("Veuillez saisir une question ou une consigne.")
    else:
        with st.spinner(f"Le satellite analyse exclusivement les données de {module_choisi}..."):
            try:
                contexte_donnees = df_filtered.to_string(index=False) if not df_filtered.empty else "Aucune donnée disponible pour ce module."
                
                prompt_complet = (
                    f"Tu es L.E.Y.L.A., l'intelligence artificielle centrale pour la gestion agricole.\n"
                    f"Structure active : {structure_courante['nom']}\n"
                    f"Module en cours d'analyse : {module_choisi}\n"
                    f"Données brutes exclusives à ce module :\n"
                    f"{contexte_donnees}\n\n"
                    f"Consigne / Question de l'administrateur : {user_query}\n\n"
                    f"Fournis une analyse professionnelle, claire et axée uniquement sur ce module."
                )
                
                historique_fictif = [{"role": "user", "content": prompt_complet}]
                reponse_satellite = rechercher_sur_le_web(historique_fictif)
                
                st.success("Rapport du Satellite L.E.Y.L.A. :")
                st.write(reponse_satellite.get("texte", ""))
                
            except Exception as e:
                st.error(f"Erreur lors de la communication avec le satellite : {e}")
