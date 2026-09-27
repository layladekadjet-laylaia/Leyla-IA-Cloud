import datetime
import hashlib
import os
import sqlite3
import uuid
from typing import Dict, List, Optional, Tuple

DB_NAME = "leyla_cloud.db"


def get_device_id() -> str:
    """Génère un identifiant unique et cohérent pour l'appareil."""
    mac = str(uuid.getnode())
    return hashlib.sha256(mac.encode()).hexdigest()[:16]


DEVICE_ID = get_device_id()

# --- INITIALISATION ET SCHÉMA ---


def init_db():
    """Initialise les tables de la base de données, effectue les migrations et crée les index."""
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        # Table des messages
        c.execute(
            """CREATE TABLE IF NOT EXISTS messages 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      device_id TEXT, 
                      session_id TEXT, 
                      role TEXT, 
                      content TEXT,
                      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
        )

        # MIGRATION AUTOMATIQUE : Vérifie si la colonne timestamp existe
        c.execute("PRAGMA table_info(messages)")
        colonnes = [col[1] for col in c.fetchall()]
        if "timestamp" not in colonnes:
            c.execute(
                "ALTER TABLE messages ADD COLUMN timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            )

        # Table des métadonnées des sessions
        c.execute(
            """CREATE TABLE IF NOT EXISTS sessions 
                     (session_id TEXT PRIMARY KEY, 
                      device_id TEXT, 
                      name TEXT, 
                      created_at TIMESTAMP)"""
        )

        # Table du profil utilisateur
        c.execute(
            """CREATE TABLE IF NOT EXISTS user_profile 
                     (device_id TEXT PRIMARY KEY, 
                      user_name TEXT,
                      title TEXT DEFAULT 'Mon Professeur')"""
        )

        # Index d'optimisation
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(device_id, session_id)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_device ON sessions(device_id)"
        )

        conn.commit()


# --- GESTION DE L'UTILISATEUR ---


def save_user_name(name: str, device_id: Optional[str] = None):
    """Enregistre le nom de l'utilisateur dans la base SQLite."""
    dev_id = device_id or DEVICE_ID
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO user_profile (device_id, user_name) 
                     VALUES (?, ?) 
                     ON CONFLICT(device_id) DO UPDATE SET user_name = excluded.user_name""",
            (dev_id, name),
        )
        conn.commit()


def get_user_name(device_id: Optional[str] = None) -> Optional[str]:
    """Récupère le nom de l'utilisateur."""
    dev_id = device_id or DEVICE_ID
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT user_name FROM user_profile WHERE device_id = ?", (dev_id,)
        )
        row = c.fetchone()
        if row:
            return row[0]

    if os.path.exists("user_name.txt"):
        with open("user_name.txt", "r", encoding="utf-8") as f:
            name = f.read().strip()
            if name:
                save_user_name(name, dev_id)
                return name
    return None


# --- GESTION DES SESSIONS & MESSAGES ---


def get_all_sessions(device_id: Optional[str] = None) -> List[Tuple[str, str]]:
    """Récupère la liste de toutes les sessions."""
    dev_id = device_id or DEVICE_ID
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT s.session_id, IFNULL(s.name, s.session_id) 
            FROM sessions s
            WHERE s.device_id = ?
            ORDER BY s.created_at DESC
        """,
            (dev_id,),
        )
        return c.fetchall()


def save_message(
    session_id: str,
    role: str,
    content: str,
    device_id: Optional[str] = None,
):
    """Sauvegarde un message et crée la session si elle n'existe pas encore."""
    dev_id = device_id or DEVICE_ID
    now = datetime.datetime.now()

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        # 1. Sauvegarde du message
        c.execute(
            "INSERT INTO messages (device_id, session_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
            (dev_id, session_id, role, content, now),
        )

        # 2. Vérification/Création de la session
        c.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        if c.fetchone() is None:
            default_name = (
                content[:25] + "..." if len(content) > 25 else content
            )
            if not default_name.strip():
                default_name = f"Discussion du {now.strftime('%d/%m/%Y')}"

            c.execute(
                "INSERT INTO sessions (session_id, device_id, name, created_at) VALUES (?, ?, ?, ?)",
                (session_id, dev_id, default_name, now),
            )

        conn.commit()


def get_history(
    session_id: str, device_id: Optional[str] = None
) -> List[Dict[str, str]]:
    """Récupère l'historique complet d'une session."""
    dev_id = device_id or DEVICE_ID
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT role, content FROM messages WHERE device_id = ? AND session_id = ? ORDER BY id ASC",
            (dev_id, session_id),
        )
        rows = c.fetchall()
        return [{"role": row[0], "content": row[1]} for row in rows]


# --- ACTIONS SUR LES SESSIONS ---


def rename_session(
    session_id: str, new_name: str, device_id: Optional[str] = None
):
    """Renomme une session."""
    dev_id = device_id or DEVICE_ID
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE sessions SET name = ? WHERE session_id = ? AND device_id = ?",
            (new_name, session_id, dev_id),
        )
        conn.commit()


def delete_session(session_id: str, device_id: Optional[str] = None):
    """Supprime définitivement une session et ses messages."""
    dev_id = device_id or DEVICE_ID
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM messages WHERE session_id = ? AND device_id = ?",
            (session_id, dev_id),
        )
        c.execute(
            "DELETE FROM sessions WHERE session_id = ? AND device_id = ?",
            (session_id, dev_id),
        )
        conn.commit()


def clear_history(device_id: Optional[str] = None):
    """Purge toutes les données de l'appareil."""
    dev_id = device_id or DEVICE_ID
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM messages WHERE device_id = ?", (dev_id,))
        c.execute("DELETE FROM sessions WHERE device_id = ?", (dev_id,))
        conn.commit()
