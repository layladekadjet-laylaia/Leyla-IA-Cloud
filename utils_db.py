import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv("config.env")

def obtenir_chaine_connexion() -> str:
    """
    Génère la chaîne de connexion SQLAlchemy à partir du fichier config.env.
    Prend en charge : postgresql, mysql, mssql (SQL Server), oracle, sqlite.
    """
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "")
    user = os.getenv("DB_USER", "")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "entreprise.db")

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
    # Garde-fou de sécurité : Seules les requêtes SELECT sont autorisées
    requete_propre = requete_sql.strip().upper()
    if not requete_propre.startswith("SELECT") and not requete_propre.startswith("WITH"):
        return "Erreur de sécurité : Seules les requêtes de lecture (SELECT) sont autorisées."

    try:
        url_connexion = obtenir_chaine_connexion()
        engine = create_engine(url_connexion)

        with engine.connect() as conn:
            df = pd.read_sql_query(text(requete_sql), conn)
            
            if df.empty:
                return "La requête a été exécutée avec succès, mais aucun résultat n'a été trouvé."
            
            # Limiter l'affichage à 50 lignes pour éviter d'inonder le contexte du modèle
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

        with engine.connect() as conn:
            db_type = os.getenv("DB_TYPE", "sqlite").lower()
            
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
