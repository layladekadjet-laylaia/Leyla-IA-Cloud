import os
import pandas as pd
from sqlalchemy import create_engine, text

# Détection et lecture dynamique des accès depuis secrets.toml ou Streamlit
def charger_configuration_db():
    try:
        import streamlit as st
        if "database" in st.secrets:
            return st.secrets["database"]
    except Exception:
        pass

    # Fallback pour exécution hors Streamlit (script pur ou .exe)
    chemin_secrets = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(chemin_secrets):
        try:
            import tomllib  # Python 3.11+
            with open(chemin_secrets, "rb") as f:
                config = tomllib.load(f)
                return config.get("database", {})
        except ImportError:
            import toml
            with open(chemin_secrets, "r", encoding="utf-8") as f:
                config = toml.load(f)
                return config.get("database", {})

    return {}

def obtenir_chaine_connexion() -> str:
    """
    Génère la chaîne de connexion SQLAlchemy à partir de la configuration database.
    """
    db_config = charger_configuration_db()

    db_type = db_config.get("db_type", "sqlite").lower()
    host = db_config.get("host", "localhost")
    port = db_config.get("port", "")
    user = db_config.get("user", "")
    password = db_config.get("password", "")
    database = db_config.get("database", "entreprise.db")

    if db_type == "sqlite":
        return f"sqlite:///{database}"
    elif db_type == "postgresql":
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    elif db_type == "mysql":
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    elif db_type == "mssql":
        return f"mssql+pyodbc://{user}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
    elif db_type == "oracle":
        return f"oracle+cx_oracle://{user}:{password}@{host}:{port}/?service_name={database}"
    else:
        raise ValueError(f"Type de base de données non supporté : {db_type}")

def interroger_base_donnees(requete_sql: str) -> str:
    """
    Exécute une requête SQL en LECTURE SEULE sur la base de données de l'entreprise
    et renvoie le résultat sous forme de texte structuré.
    
    Args:
        requete_sql (str): La requête SQL à exécuter (ex: SELECT * FROM stocks LIMIT 10)
    """
    # Garde-fou de sécurité : Seules les requêtes SELECT et WITH sont autorisées
    requete_propre = requete_sql.strip().upper()
    if not (requete_propre.startswith("SELECT") or requete_propre.startswith("WITH")):
        return "Erreur de sécurité : Seules les requêtes de lecture (SELECT / WITH) sont autorisées."

    try:
        url_connexion = obtenir_chaine_connexion()
        engine = create_engine(url_connexion)

        with engine.connect() as conn:
            df = pd.read_sql_query(text(requete_sql), conn)
            
            if df.empty:
                return "La requête a été exécutée avec succès, mais aucun résultat n'a été trouvé."
            
            # Limiter l'affichage à 50 lignes pour préserver le contexte du modèle
            if len(df) > 50:
                aperçu = df.head(50).to_markdown(index=False)
                return f"{aperçu}\n\n*(Note : Affichage limité aux 50 premières lignes sur {len(df)} au total)*"
            
            return df.to_markdown(index=False)

    except Exception as e:
        return f"Erreur lors de l'exécution de la requête SQL : {str(e)}"

def lister_tables_et_structure() -> str:
    """
    Permet à Leyla d'explorer la structure de la base de données (tables et colonnes)
    afin de pouvoir construire des requêtes SQL précises par elle-même.
    """
    try:
        url_connexion = obtenir_chaine_connexion()
        engine = create_engine(url_connexion)
        db_config = charger_configuration_db()
        db_type = db_config.get("db_type", "sqlite").lower()

        with engine.connect() as conn:
            if db_type == "sqlite":
                query = "SELECT name FROM sqlite_master WHERE type='table';"
            elif db_type in ["postgresql", "mysql"]:
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
            elif db_type == "mssql":
                query = "SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE';"
            else:
                return "Inspection des tables non supportée automatiquement pour ce SGBD."

            df = pd.read_sql_query(text(query), conn)
            if df.empty:
                return "Aucune table trouvée dans la base de données."
            
            tables = df.iloc[:, 0].tolist()
            return f"Tables disponibles dans la base de données : {', '.join(tables)}"

    except Exception as e:
        return f"Impossible de récupérer le schéma de la base de données : {str(e)}"
