from typing import Optional
import streamlit as st
import pandas as pd
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

def charger_donnees_module(module_choisi: str) -> pd.DataFrame:
    """Récupère la table unique Supabase et filtre selon le module exécuté."""
    if not supabase:
        return pd.DataFrame()
    try:
        # On interroge toujours la vraie table unique où tout est enregistré
        response = supabase.table("producteurs_parcelles").select("*").execute()
        data = response.data
        if data:
            df_global = pd.DataFrame(data)
            
            # Si la colonne de suivi des modules existe, on filtre les lignes
            if "module_execute" in df_global.columns:
                # Normalisation pour correspondre aux libellés du selectbox
                if "Géolocalisation" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Géo", case=False, na=False)]
                elif "Diagnostic" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Diagnostic", case=False, na=False)]
                elif "Rendement" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("Rendement", case=False, na=False)]
                elif "PDC" in module_choisi:
                    return df_global[df_global["module_execute"].str.contains("PDC|Développement", case=False, na=False)]
            
            return df_global
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données Supabase : {e}")
        return pd.DataFrame()


# ==========================================
# 2. INTERFACE DU SERVEUR CENTRAL
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

# Mapping entre le choix de l'interface et les tables Supabase correspondantes
# (Vous pourrez adapter les noms des tables selon vos créations sur Supabase)
mapping_tables = {
    "Géolocalisation & RDUE (Parcelles)": "producteurs_parcelles",
    "Diagnostic Phytosanitaire": "diagnostic_parcelles",
    "Estimation de Rendement": "estimations_rendement",
    "Plan de Développement (PDC)": "pdc_cacaoyeres"
}

table_active = mapping_tables[module_choisi]

# Chargement des données de la table active
df = charger_donnees_module(table_active)

st.subheader(f"📊 Données en direct : {module_choisi}")
st.markdown(f"*Source Supabase : table `{table_active}`*")

if not df.empty:
    st.dataframe(df, use_container_width=True)
else:
    st.info(f"Aucune donnée enregistrée pour le moment dans la table `{table_active}`. En attente de synchronisation depuis la tablette terrain.")

st.divider()

# ==========================================
# 3. INTERACTION AVEC LE SATELLITE IA (HUB UNIVERSEL)
# ==========================================
st.subheader("🤖 Assistant IA L.E.Y.L.A. (Analyse Experte Dynamique)")
st.markdown("Posez n'importe quelle question sur les données du module sélectionné (ex: *'Quelles sont les maladies dominantes ?'* ou *'Fais-moi un rapport de synthèse'*).")

user_query = st.text_input("Votre requête pour le satellite :")

if st.button("Lancer l'analyse du satellite"):
    if not user_query:
        st.warning("Veuillez saisir une question ou une consigne.")
    else:
        with st.spinner(f"Le satellite analyse les données du module {module_choisi}..."):
            try:
                contexte_donnees = df.to_string(index=False) if not df.empty else "Aucune donnée disponible dans cette table."
                
                prompt_complet = (
                    f"Tu es L.E.Y.L.A., l'intelligence artificielle centrale pour la gestion agricole.\n"
                    f"Module analysé : {module_choisi}\n"
                    f"Données brutes extraites de Supabase ({table_active}) :\n"
                    f"{contexte_donnees}\n\n"
                    f"Consigne / Question de l'administrateur : {user_query}\n\n"
                    f"Fournis une analyse professionnelle, détaillée et structurée."
                )
                
                historique_fictif = [{"role": "user", "content": prompt_complet}]
                reponse_satellite = rechercher_sur_le_web(historique_fictif)
                
                st.success("Rapport du Satellite L.E.Y.L.A. :")
                st.write(reponse_satellite.get("texte", ""))
                
            except Exception as e:
                st.error(f"Erreur lors de la communication avec le satellite : {e}")
