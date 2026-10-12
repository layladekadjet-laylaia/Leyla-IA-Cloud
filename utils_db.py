import os
import sys
import urllib.parse
import pandas as pd
from sqlalchemy import create_engine, text

def charger_configuration_db() -> dict:
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
                # Tentative avec tomllib (Python 3.11+)
                import tomllib
                with open(chemin, "rb") as f:
                    config = tomllib.load(f)
                    return config.get("database", {})
            except ImportError:
                try:
                    # Fallback sur le paquet externe toml
                    import toml
                    with open(chemin, "r", encoding="utf-8") as f:
                        config = toml.load(f)
                        return config.get("database", {})
                except Exception:
                    continue
            except Exception:
                continue

    return {}


def obtenir_chaine_connexion() -> tuple[str, str]:
    """
    Génère dynamiquement la chaîne de connexion SQLAlchemy et retourne aussi le type de SGBD.
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
        return f"sqlite:///{database}", db_type

    # Échappement sécurisé des identifiants
    user_encoded = urllib.parse.quote_plus(user)
    password_encoded = urllib.parse.quote_plus(password)
    host_port = f"{host}:{port}" if port else host

    # Cas 2 : Bases de données réseau distantes
    if db_type == "postgresql":
        return f"postgresql://{user_encoded}:{password_encoded}@{host_port}/{database}", db_type
    elif db_type == "mysql":
        return f"mysql+pymysql://{user_encoded}:{password_encoded}@{host_port}/{database}", db_type
    elif db_type == "mssql":
        driver = "ODBC+Driver+17+for+SQL+Server"
        return f"mssql+pyodbc://{user_encoded}:{password_encoded}@{host_port}/{database}?driver={driver}", db_type
    elif db_type == "oracle":
        return f"oracle+cx_oracle://{user_encoded}:{password_encoded}@{host_port}/?service_name={database}", db_type
    else:
        raise ValueError(f"Type de base de données non supporté : {db_type}")


def interroger_base_donnees(requete_sql: str) -> str:
    """
    Exécute une requête SQL en LECTURE SEULE de manière sécurisée sur la base configurée.
    """
    # Nettoyage et vérification stricte anti-injection / écriture
    requete_propre = requete_sql.strip()
    requete_upper = requete_propre.upper()

    if not (requete_upper.startswith("SELECT") or requete_upper.startswith("WITH")):
        return "Erreur de sécurité : Seules les requêtes de lecture (SELECT / WITH) sont autorisées."
    
    # Interdiction des points-virgules multiples pour éviter l'empilement de requêtes (SQL Injection)
    if ";" in requete_propre.rstrip(";"):
        return "Erreur de sécurité : Les requêtes multiples (point-virgule intermédiaire) sont interdites."

    try:
        url_connexion, db_type = obtenir_chaine_connexion()
        
        # Configuration spécifique de l'engine selon le SGBD
        if db_type == "sqlite":
            engine = create_engine(url_connexion)
        else:
            engine = create_engine(url_connexion, connect_args={'connect_timeout': 10})

        with engine.connect() as conn:
            df = pd.read_sql_query(text(requete_propre), conn)
            
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
    Permet à Leyla d'explorer la structure de la base de données cliente en toute sécurité.
    """
    try:
        url_connexion, db_type = obtenir_chaine_connexion()
        db_config = charger_configuration_db()

        if db_type == "sqlite":
            engine = create_engine(url_connexion)
        else:
            engine = create_engine(url_connexion, connect_args={'connect_timeout': 10})

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
            host_info = db_config.get('host', 'local')
            return f"Tables disponibles sur le serveur ({host_info}) : {', '.join(tables)}"

    except Exception as e:
        return f"Impossible de récupérer la structure sur ce serveur : {str(e)}"
