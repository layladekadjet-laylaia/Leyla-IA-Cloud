import sqlite3
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import streamlit as st
import pandas as pd

# IMPORTATION DU CERVEAU DE LEYLA (Le Satellite)
# Assurez-vous que le nom de votre fichier correspond bien (ex: recherche_ia.py)
from recherche_ia import rechercher_sur_le_web

# ==========================================
# 1. CONFIGURATION DE LA BASE DE DONNÉES (SQLITE)
# ==========================================

DB_NAME = "leyla_serveur_central.db"

def init_db():
    """Crée les tables relationnelles si elles n'existent pas."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS producteurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cooperative TEXT,
            section TEXT,
            technicien TEXT,
            nom_producteur TEXT,
            code_producteur TEXT,
            superficie REAL,
            age_cacaoyere INTEGER,
            polygone_gps TEXT,
            statut_rdue TEXT,
            date_synchro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. APPLICATION API FASTAPI (Réception des tablettes)
# ==========================================

app = FastAPI(title="Serveur Central L.E.Y.L.A.", version="1.0")

class DonnesTerrain(BaseModel):
    cooperative: str
    section: str
    technicien: str
    nom_producteur: str
    code_producteur: Optional[str] = "NON-ATTRIBUE"
    superficie: float
    age_cacaoyere: int
    polygone_gps: str
    statut_rdue: str

@app.post("/api/sync")
def synchroniser_donnees(donnees: DonnesTerrain):
    """Route API interceptant la synchronisation des tablettes de terrain."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO producteurs (cooperative, section, technicien, nom_producteur, code_producteur, superficie, age_cacaoyere, polygone_gps, statut_rdue)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            donnees.cooperative,
            donnees.section,
            donnees.technicien,
            donnees.nom_producteur,
            donnees.code_producteur,
            donnees.superficie,
            donnees.age_cacaoyere,
            donnees.polygone_gps,
            donnees.statut_rdue
        ))
        
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Données de {donnees.nom_producteur} bien enregistrées sur le serveur central L.E.Y.L.A."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 3. INTERFACE STREAMLIT (Dashboard & Appel au Satellite Leyla)
# ==========================================

def run_dashboard():
    st.set_page_config(page_title="L.E.Y.L.A. - Serveur Central", layout="wide")
    st.title("🌐 L.E.Y.L.A. - Tableau de Bord du Serveur Central")
    st.markdown("*Plateforme de centralisation, d'analyse RDUE et d'intelligence artificielle pour les Coopératives et le Régulateur.*")

    # Connexion à la base de données pour charger les données
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM producteurs", conn)
    conn.close()

    # Barre latérale de filtrage hiérarchique
    st.sidebar.header("🔍 Filtres Hiérarchiques")
    if not df.empty:
        coops = ["Toutes"] + list(df["cooperative"].unique())
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
        superficie_totale = df_filtered["superficie"].sum() if not df_filtered.empty else 0.0
        st.metric("Superficie Totale (Hectares)", f"{superficie_totale:.2f} ha")
    with col3:
        conformes = len(df_filtered[df_filtered["statut_rdue"].str.contains("conforme", case=False, na=False)]) if not df_filtered.empty else 0
        st.metric("Parcelles Conformes RDUE", conformes)

    st.divider()

    # Visualisation des données tabulaires
    st.subheader("📋 Registre Centralisé des Parcelles")
    if not df_filtered.empty:
        st.dataframe(df_filtered, use_container_width=True)
    else:
        st.info("Aucune donnée disponible pour le moment. En attente de synchronisation depuis les tablettes de terrain.")

    st.divider()

    # ==========================================
    # 4. UTILISATION DU "SATELLITE" (recherche_ia.py)
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
                    # Préparation des données de la base sous forme de texte pour le contexte
                    contexte_donnees = df_filtered.to_string(index=False) if not df_filtered.empty else "Aucune donnée enregistrée."
                    
                    # On structure l'historique que va recevoir le satellite (recherche_ia.py)
                    prompt_complet = (
                        f"Voici les données factuelles extraites de la base du serveur central agricole :\n"
                        f"{contexte_donnees}\n\n"
                        f"Question de l'administrateur / régulateur : {user_query}"
                    )
                    
                    historique_fictif = [{"role": "user", "content": prompt_complet}]
                    
                    # Appel de la fonction de votre fichier recherche_ia.py
                    reponse_satellite = rechercher_sur_le_web(historique_fictif)
                    
                    st.success("Réponse du Serveur Central L.E.Y.L.A. :")
                    st.write(reponse_satellite.get("texte", ""))
                    
                except Exception as e:
                    st.error(f"Erreur lors de la communication avec le satellite IA : {e}")

if __name__ == "__main__":
    run_dashboard()
