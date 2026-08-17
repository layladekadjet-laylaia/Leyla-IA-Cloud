import sqlite3
import uuid
import hashlib
import os

DB_NAME = 'leyla_cloud.db'

def save_user_name(name):
    with open("user_name.txt", "w") as f:
        f.write(name)

def get_user_name():
    if os.path.exists("user_name.txt"):
        with open("user_name.txt", "r") as f:
            return f.read()
    return None

def get_device_id():
    """Génère un identifiant unique basé sur l'adresse MAC de l'appareil."""
    mac = str(uuid.getnode())
    return hashlib.sha256(mac.encode()).hexdigest()[:16]

DEVICE_ID = get_device_id()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Ajout de la colonne session_id pour isoler les différentes discussions
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  device_id TEXT, 
                  session_id TEXT, 
                  role TEXT, 
                  content TEXT)''')
    conn.commit()
    conn.close()

def get_all_sessions(device_id=None):
    """Récupère la liste de toutes les sessions distinctes pour cet appareil."""
    dev_id = device_id if device_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT DISTINCT session_id FROM messages WHERE device_id = ?", (dev_id,))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def save_message(session_id, role, content, device_id=None):
    """Sauvegarde un message dans une session spécifique."""
    dev_id = device_id if device_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO messages (device_id, session_id, role, content) VALUES (?, ?, ?, ?)", 
              (dev_id, session_id, role, content))
    conn.commit()
    conn.close()

def get_history(session_id, device_id=None):
    """Récupère l'historique d'une session spécifique."""
    dev_id = device_id if device_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE device_id = ? AND session_id = ?", (dev_id, session_id))
    rows = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

def clear_session(session_id, device_id=None):
    """Efface une session de discussion spécifique."""
    dev_id = device_id if device_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE device_id = ? AND session_id = ?", (dev_id, session_id))
    conn.commit()
    conn.close()
