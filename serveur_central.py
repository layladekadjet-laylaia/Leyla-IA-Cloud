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

def charger_donnees_isolees(module_choisi: str) -> pd.DataFrame:
    """Récupère la table unique Supabase et isole strictement les données du module."""
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table("producteurs_parcelles").select("*").execute()
        data = response.data
        if data:
            df_global = pd.DataFrame(data)
            
            if "module_execute" in df_global.columns:
                # Filtrage strict et étanche selon le module actif
                if "Géolocalisation" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Géo", case=False, na=False)].reset_index(drop=True)
                elif "Diagnostic" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Diagnostic", case=False, na=False)].reset_index(drop=True)
                elif "Rendement" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Rendement", case=False, na=False)].reset_index(drop=True)
                elif "PDC" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("PDC|Développement", case=False, na=False)].reset_index(drop=True)
            
            return pd.DataFrame()
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données Supabase : {e}")
        return pd.DataFrame()

# ==========================================
# 2. MOTEUR D'ANALYSE DÉCISIONNELLE LEÏLA (PDC)
# ==========================================
def leila_analyse_pdc_metier(donnees_producteur: dict):
    """
    Module d'analyse automatique de Leïla basé sur les données
    d'un PDC spécifique synchronisé depuis la tablette.
    """
    nom = donnees_producteur.get("nom_producteur", "Inconnu")
    code = donnees_producteur.get("code_producteur", "N/A")
    
    # Extraire les objets JSON / dictionnaires enregistrés
    reponses = donnees_producteur.get("reponses_pdc", {})
    if isinstance(reponses, str):
        try:
            reponses = json.loads(reponses)
        except Exception:
            reponses = {}

    st.markdown(f"### 🤖 Diagnostic de Leïla pour le PDC de **{nom}** (Code: `{code}`)")
    
    # Extraction des indicateurs clés
    score_sante = reponses.get("score_pression_sanitaire", 0)
    solde_net = reponses.get("solde_net_estime", 0)
    toposequence = reponses.get("toposequence", "Non spécifiée")
    tendance = reponses.get("tendance_production_3ans_pct", 0)
    part_cacao = reponses.get("part_revenu_cacao_pct", 100)

    # 1. ÉVALUATION AGRONOMIQUE
    st.markdown("**🌱 1. Situation Agronomique & Fitosanitaire**")
    if score_sante <= 3:
        st.success("• **Pression sanitaire faible :** Verger globalement sain et bien entretenu.")
    elif score_sante <= 7:
        st.warning("• **Pression sanitaire modérée :** Risques identifiés sur le verger (gourmands, ombrage ou attaques ponctuelles).")
    else:
        st.error("• **Pression sanitaire critique :** Actions phytosanitaires et taille d'urgence requises.")

    if toposequence in ["Bas-fond", "Bas de versant"]:
        st.warning(f"• **Risque Toposéquence ({toposequence}) :** Attention au risque de saturation en eau et d'asphyxie racinaire.")

    # 2. ÉVALUATION ÉCONOMIQUE
    st.markdown("**📊 2. Bilan Économique du Foyer**")
    col_e1, col_e2, col_e3 = st.columns(3)
    col_e1.metric("Solde Net Estimé", f"{solde_net:,.0f} FCFA")
    col_e2.metric("Évolution Prod. (3 ans)", f"{tendance:+.1f}%")
    col_e3.metric("Part Revenu Cacao", f"{part_cacao:.1f}%")

    # 3. RECOMMANDATIONS
    st.markdown("**💡 3. Orientation & Plan d'Action Recommandé**")
    recommandations = []
    if score_sante > 5:
        recommandations.append("Prioriser un chantier d'égourmandage et d'assainissement de la crown.")
    if solde_net > 200000:
        recommandations.append("Capacité de financement présente : Planifier un plan de fertilisation raisonnée.")
    else:
        recommandations.append("Marge financière faible : Orienter le producteur vers le compostage et les intrants subventionnés.")
    if part_cacao > 85:
        recommandations.append("Proposer une diversification agricole (intégration de cultures vivrières/arbres d'ombrage à valeur).")

    for i, rec in enumerate(recommandations, 1):
        st.write(f"**{i}.** {rec}")

# ==========================================
# 3. INTERFACE DU SERVEUR CENTRAL
# ==========================================
st.title("🌐 L.E.Y.L.A. - Centre de Commandement Global")
st.markdown("*Plateforme unifiée d'analyse multi-modules et d'intelligence artificielle pour les Coopératives.*")

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

# Chargement strict des données du module sélectionné
df_filtered = charger_donnees_isolees(module_choisi)

st.subheader(f"📊 Module actif : {module_choisi}")

# Affichage du tableau dans un bloc déroulant
with st.expander(f"📁 Afficher / Masquer les données brutes ({len(df_filtered)} enregistrement(s))", expanded=False):
    if not df_filtered.empty:
        st.dataframe(df_filtered, use_container_width=True)
    else:
        st.info(f"Aucune donnée enregistrée spécifiquement pour le module : {module_choisi}.")

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
