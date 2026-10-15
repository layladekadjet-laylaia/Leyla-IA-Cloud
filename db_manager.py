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
    """Initialise les tables de la base de données de manière totalement sécurisée."""
    with sqlite3.connect(DB_NAME, timeout=5.0) as conn:
        c = conn.cursor()

        # 1. Table des messages
        c.execute(
            """CREATE TABLE IF NOT EXISTS messages 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      device_id TEXT, 
                      session_id TEXT, 
                      role TEXT, 
                      content TEXT,
                      timestamp TIMESTAMP)"""
        )

        try:
            c.execute("ALTER TABLE messages ADD COLUMN timestamp TIMESTAMP")
        except sqlite3.OperationalError:
            pass

        # 2. Table des métadonnées des sessions
        c.execute(
            """CREATE TABLE IF NOT EXISTS sessions 
                     (session_id TEXT PRIMARY KEY, 
                      device_id TEXT, 
                      name TEXT, 
                      created_at TIMESTAMP)"""
        )

        # 3. Table du profil utilisateur
        c.execute(
            """CREATE TABLE IF NOT EXISTS user_profile 
                     (device_id TEXT PRIMARY KEY, 
                      user_name TEXT,
                      title TEXT DEFAULT 'Mon Professeur')"""
        )

        # 4. Table du coffre-fort de credentials (Sécurité matérielle)
        c.execute(
            """CREATE TABLE IF NOT EXISTS device_credentials 
                     (device_id TEXT, ip_address TEXT, username TEXT, password TEXT, 
                      PRIMARY KEY(device_id, ip_address))"""
        )

        # 5. Index d'optimisation
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(device_id, session_id)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_device ON sessions(device_id)"
        )

        conn.commit()


# --- GESTION DES CREDENTIALS MATÉRIELS ---


def save_device_credentials(ip: str, username: str, password: str, device_id: Optional[str] = None):
    """Enregistre ou met à jour les identifiants d'un appareil sécurisé."""
    dev_id = device_id or DEVICE_ID
    with sqlite3.connect(DB_NAME, timeout=5.0) as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO device_credentials (device_id, ip_address, username, password) 
                     VALUES (?, ?, ?, ?) 
                     ON CONFLICT(device_id, ip_address) DO UPDATE SET username = excluded.username, password = excluded.password""",
            (dev_id, ip, username, password),
        )
        conn.commit()


def get_device_credentials(ip: str, device_id: Optional[str] = None) -> dict:
    """Récupère les identifiants d'un appareil enregistré."""
    dev_id = device_id or DEVICE_ID
    with sqlite3.connect(DB_NAME, timeout=5.0) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT username, password FROM device_credentials WHERE device_id = ? AND ip_address = ?", 
            (dev_id, ip)
        )
        row = c.fetchone()
        if row:
            return {"username": row[0], "password": row[1]}
    return {"username": "admin", "password": "12345"}


# --- GESTION DE L'UTILISATEUR ---


def save_user_name(name: str, device_id: Optional[str] = None):
    """Enregistre le nom de l'utilisateur dans la base SQLite."""
    dev_id = device_id or DEVICE_ID
    with sqlite3.connect(DB_NAME, timeout=5.0) as conn:
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
    with sqlite3.connect(DB_NAME, timeout=5.0) as conn:
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
    with sqlite3.connect(DB_NAME, timeout=5.0) as conn:
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

    with sqlite3.connect(DB_NAME, timeout=5.0) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO messages (device_id, session_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
            (dev_id, session_id, role, content, now),
        )

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
    with sqlite3.connect(DB_NAME, timeout=5.0) as conn:
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
    with sqlite3.connect(DB_NAME, timeout=5.0) as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE sessions SET name = ? WHERE session_id = ? AND device_id = ?",
            (new_name, session_id, dev_id),
        )
        conn.commit()


def delete_session(session_id: str, device_id: Optional[str] = None):
    """Supprime définitivement une session et ses messages."""
    dev_id = device_id or DEVICE_ID
    with sqlite3.connect(DB_NAME, timeout=5.0) as conn:
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
    with sqlite3.connect(DB_NAME, timeout=5.0) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM messages WHERE device_id = ?", (dev_id,))
        c.execute("DELETE FROM sessions WHERE device_id = ?", (dev_id,))
        conn.commit()
