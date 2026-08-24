from typing import Optional
import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ==========================================
# 0. CONFIGURATION DE LA PAGE STREAMLIT
# ==========================================
st.set_page_config(
    page_title="L.E.Y.L.A. - Serveur Central",
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

def charger_donnees_supabase() -> pd.DataFrame:
    """Récupère toutes les données de la table Supabase."""
    if not supabase:
        return pd.DataFrame()
    try:
        # Interrogation de la table centrale des producteurs/parcelles
        response = supabase.table("producteurs_parcelles").select("*").execute()
        data = response.data
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données Supabase : {e}")
        return pd.DataFrame()

# ==========================================
# 2. INTERFACE STREAMLIT DU SERVEUR CENTRAL
# ==========================================
st.title("🌐 L.E.Y.L.A. - Tableau de Bord du Serveur Central")
st.markdown("*Plateforme de centralisation, d'analyse RDUE et d'intelligence artificielle pour les Coopératives et le Régulateur.*")

# Charger les données en direct de Supabase
df = charger_donnees_supabase()

# Barre latérale de filtrage hiérarchique
st.sidebar.header("🔍 Filtres Hiérarchiques")
if not df.empty and "cooperative" in df.columns:
    coops = ["Toutes"] + list(df["cooperative"].dropna().unique())
    selected_coop = st.sidebar.selectbox("Sélectionner la Coopérative", coops)

    if selected_coop != "Toutes":
        df_filtered = df[df["cooperative"] == selected_coop]
    else:
        df_filtered = df
else:
    df_filtered = df

# Affichage des métriques principales
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Producteurs Enregistrés", len(df_filtered))
with col2:
    superficie_totale = df_filtered["superficie"].sum() if not df_filtered.empty and "superficie" in df_filtered else 0.0
    st.metric("Superficie Totale (Hectares)", f"{superficie_totale:.2f} ha")
with col3:
    conformes = len(df_filtered[df_filtered["statut_rdue"].str.contains("conforme", case=False, na=False)]) if not df_filtered.empty and "statut_rdue" in df_filtered else 0
    st.metric("Parcelles Conformes RDUE", conformes)

st.divider()

# Visualisation des données tabulaires
st.subheader("📋 Registre Centralisé des Parcelles (Supabase)")
if not df_filtered.empty:
    st.dataframe(df_filtered, use_container_width=True)
else:
    st.info("Aucune donnée disponible pour le moment dans Supabase. En attente de synchronisation terrain.")

st.divider()

# ==========================================
# 3. UTILISATION DU "SATELLITE" (recherche_ia.py)
# ==========================================
st.subheader("🤖 Assistant IA L.E.Y.L.A. (Requêtes en Langage Naturel)")
st.markdown("Posez vos questions sur les données centralisées (ex: *'Quel est l'état des parcelles pour la section Méagué ?'*).")

user_query = st.text_input("Votre question à L.E.Y.L.A. :")

if st.button("Interroger L.E.Y.L.A."):
    if not user_query:
        st.warning("Veuillez saisir une question.")
    else:
        with st.spinner("Le satellite Leyla analyse les données en orbite..."):
            try:
                contexte_donnees = df_filtered.to_string(index=False) if not df_filtered.empty else "Aucune donnée enregistrée."
                
                prompt_complet = (
                    f"Voici les données factuelles extraites de la base Supabase du serveur central agricole :\n"
                    f"{contexte_donnees}\n\n"
                    f"Question de l'administrateur / régulateur : {user_query}"
                )
                
                historique_fictif = [{"role": "user", "content": prompt_complet}]
                reponse_satellite = rechercher_sur_le_web(historique_fictif)
                
                st.success("Réponse du Serveur Central L.E.Y.L.A. :")
                st.write(reponse_satellite.get("texte", ""))
                
            except Exception as e:
                st.error(f"Erreur lors de la communication avec le satellite IA : {e}")
