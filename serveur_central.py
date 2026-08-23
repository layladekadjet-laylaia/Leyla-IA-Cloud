import sqlite3
from typing import List, Optional
from fastapi import FastAPI, HTTPException
import google.generativeai as genai
pydantic_v1_compat = True  # Pour la compatibilité avec certains modules de pydantic
from pydantic import BaseModel
import streamlit as st
import pandas as pd

# ==========================================
# 1. CONFIGURATION DE LA BASE DE DONNÉES (SQLITE)
# ==========================================

DB_NAME = "leyla_serveur_central.db"

def init_db():
    """Crée les tables relationnelles si elles n'existent pas."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Table des Coopératives et Sections
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
        return {"status": "success", "message": f"Données de {donnees.nom_producteur} bien enregistrées et sécurisées sur le serveur central L.E.Y.L.A."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 3. INTERFACE STREAMLIT (Dashboard & Assistant RAG Gemini)
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
        st.info("Aucune donnée disponible pour le moment. En synchronisez depuis le mode terrain.")

    st.divider()

    # ==========================================
    # 4. MODULE RAG / ASSISTANT IA GEMINI
    # ==========================================
    st.subheader("🤖 Assistant IA L.E.Y.L.A. (Requêtes en Langage Naturel)")
    st.markdown("Posez vos questions sur les données centralisées (ex: *'Quel est l'état des parcelles pour la section Méagué ?'*).")

    user_query = st.text_input("Votre question à L.E.Y.L.A. :")
    
    # Récupération de la clé API (à configurer via les secrets Streamlit ou une variable d'environnement)
    api_key = st.secrets.get("GEMINI_API_KEY", "VOTRE_CLE_API_ICI")

    if st.button("Interroger L.E.Y.L.A."):
        if not user_query:
            st.warning("Veuillez saisir une question.")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Conversion des données de la base en texte brut contextuel pour l'IA (Principe du RAG)
                contexte_donnees = df_filtered.to_string(index=False) if not df_filtered.empty else "Aucune donnée enregistrée."
                
                prompt_systeme = f"""
                Tu es L.E.Y.L.A., l'intelligence artificielle du serveur central agricole.
                Voici les données extraites de la base de données SQL du serveur central :
                {contexte_donnees}
                
                Réponds à la question de l'utilisateur en te basant strictement sur ces données factuelles. 
                Sois professionnel, clair et concis (destiné aux dirigeants ou au Conseil du Café-Cacao).
                Question de l'utilisateur : {user_query}
                """
                
                response = model.generate_content(prompt_systeme)
                st.success("Réponse de L.E.Y.L.A. :")
                st.write(response.text)
                
            except Exception as e:
                st.error(f"Erreur lors de la communication avec l'API Gemini : {e}")

if __name__ == "__main__":
    run_dashboard()
