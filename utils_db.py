import os
import sys
import urllib.parse
import pandas as pd
from sqlalchemy import create_engine, text

def charger_configuration_db():
    """
    Détection et lecture dynamique des identifiants et accès réseau (IP, Port, BDD)
    depuis Streamlit secrets ou directement depuis le fichier secrets.toml local/portable.
    """
    # 1. Essai d'accès via l'API interne Streamlit
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "database" in st.secrets:
            return dict(st.secrets["database"])
    except Exception:
        pass

    # 2. Liste des chemins potentiels du fichier secrets.toml (Gestion .exe PyInstaller & local)
    chemins_recherche = [
        os.path.join(".streamlit", "secrets.toml"),
        os.path.join(os.getcwd(), ".streamlit", "secrets.toml"),
        os.path.expanduser(os.path.join("~", ".streamlit", "secrets.toml")),
    ]

    # Ajout du dossier temporaire PyInstaller s'il existe (_internal)
    if hasattr(sys, "_MEIPASS"):
        chemins_recherche.insert(0, os.path.join(sys._MEIPASS, ".streamlit", "secrets.toml"))

    for chemin in chemins_recherche:
        if os.path.exists(chemin):
            try:
                import tomllib  # Python 3.11+
                with open(chemin, "rb") as f:
                    config = tomllib.load(f)
                    return config.get("database", {})
            except ImportError:
                import toml
                with open(chemin, "r", encoding="utf-8") as f:
                    config = toml.load(f)
                    return config.get("database", {})
            except Exception:
                continue

    return {}


def obtenir_chaine_connexion() -> str:
    """
    Génère dynamiquement la chaîne de connexion SQLAlchemy à partir de la configuration.
    Gère le formatage d'IP, de ports, et l'échappement des mots de passe complexes.
    """
    db_config = charger_configuration_db()

    db_type = str(db_config.get("db_type", "sqlite")).lower().strip()
    host = str(db_config.get("host", "localhost")).strip()
    port = str(db_config.get("port", "")).strip()
    user = str(db_config.get("user", "")).strip()
    password = str(db_config.get("password", ""))
    database = str(db_config.get("database", "entreprise.db")).strip()

    # Cas 1 : Base de données SQLite Locale
    if db_type == "sqlite":
        return f"sqlite:///{database}"

    # Échappement des identifiants pour éviter les erreurs de syntaxe d'URL (mots de passe avec @ ou #)
    user_encoded = urllib.parse.quote_plus(user)
    password_encoded = urllib.parse.quote_plus(password)

    # Formatage propre du bloc [host:port]
    host_port = f"{host}:{port}" if port else host

    # Cas 2 : Bases de données réseau distantes (IP/Port)
    if db_type == "postgresql":
        return f"postgresql://{user_encoded}:{password_encoded}@{host_port}/{database}"
    elif db_type == "mysql":
        return f"mysql+pymysql://{user_encoded}:{password_encoded}@{host_port}/{database}"
    elif db_type == "mssql":
        driver = "ODBC+Driver+17+for+SQL+Server"
        return f"mssql+pyodbc://{user_encoded}:{password_encoded}@{host_port}/{database}?driver={driver}"
    elif db_type == "oracle":
        return f"oracle+cx_oracle://{user_encoded}:{password_encoded}@{host_port}/?service_name={database}"
    else:
        raise ValueError(f"Type de base de données non supporté : {db_type}")


def interroger_base_donnees(requete_sql: str) -> str:
    """
    Exécute une requête SQL en LECTURE SEULE sur la base de données configurée.
    """
    requete_propre = requete_sql.strip().upper()
    if not (requete_propre.startswith("SELECT") or requete_propre.startswith("WITH")):
        return "Erreur de sécurité : Seules les requêtes de lecture (SELECT / WITH) sont autorisées."

    try:
        url_connexion = obtenir_chaine_connexion()
        engine = create_engine(url_connexion, connect_args={'connect_timeout': 10} if "sqlite" not in url_connexion else {})

        with engine.connect() as conn:
            df = pd.read_sql_query(text(requete_sql), conn)
            
            if df.empty:
                return "La requête a été exécutée avec succès, mais aucun résultat n'a été trouvé."
            
            if len(df) > 50:
                aperçu = df.head(50).to_markdown(index=False)
                return f"{aperçu}\n\n*(Note : Affichage limité aux 50 premières lignes sur {len(df)} au total)*"
            
            return df.to_markdown(index=False)

    except Exception as e:
        return f"Erreur de connexion/exécution SQL sur la cible : {str(e)}"


def lister_tables_et_structure() -> str:
    """
    Permet à Leyla d'explorer la structure de la base de données cliente (IP courante).
    """
    try:
        url_connexion = obtenir_chaine_connexion()
        engine = create_engine(url_connexion, connect_args={'connect_timeout': 10} if "sqlite" not in url_connexion else {})
        db_config = charger_configuration_db()
        db_type = str(db_config.get("db_type", "sqlite")).lower().strip()

        with engine.connect() as conn:
            if db_type == "sqlite":
                query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            elif db_type == "postgresql":
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
            elif db_type == "mysql":
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE();"
            elif db_type == "mssql":
                query = "SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE';"
            else:
                return "Inspection des tables non supportée automatiquement pour ce SGBD."

            df = pd.read_sql_query(text(query), conn)
            if df.empty:
                return "Aucune table trouvée dans la base de données ciblée."
            
            tables = df.iloc[:, 0].tolist()
            return f"Tables disponibles sur le serveur ({db_config.get('host', 'local')}) : {', '.join(tables)}"

    except Exception as e:
        return f"Impossible de récupérer la structure sur ce serveur : {str(e)}"
