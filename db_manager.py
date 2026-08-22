import sqlite3
import uuid
import hashlib
import os
import datetime

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
    # Table avec support des sessions multiples
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  device_id TEXT, 
                  session_id TEXT, 
                  role TEXT, 
                  content TEXT)''')
    
    # NOUVELLE TABLE : Pour gérer les métadonnées des sessions (nom, date de création, etc.)
    c.execute('''CREATE TABLE IF NOT EXISTS sessions 
                 (session_id TEXT PRIMARY KEY, 
                  device_id TEXT, 
                  name TEXT, 
                  created_at TIMESTAMP)''')
                  
    conn.commit()
    conn.close()

# --- GESTION DES SESSIONS ---

def get_all_sessions(device_id=None):
    """Récupère la liste de toutes les sessions distinctes pour cet appareil, triées par date."""
    dev_id = device_id if device_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Jointure pour récupérer le nom de la session s'il existe, sinon on prend l'ID
    c.execute('''
        SELECT s.session_id, IFNULL(s.name, s.session_id) 
        FROM sessions s
        WHERE s.device_id = ?
        ORDER BY s.created_at DESC
    ''', (dev_id,))
    
    rows = c.fetchall()
    conn.close()
    # Retourne une liste de tuples (session_id, display_name)
    return rows

def save_message(session_id, role, content, device_id=None):
    """Sauvegarde un message et s'assure que la session existe dans la table sessions."""
    dev_id = device_id if device_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Sauvegarde du message
    c.execute("INSERT INTO messages (device_id, session_id, role, content) VALUES (?, ?, ?, ?)", 
              (dev_id, session_id, role, content))
              
    # 2. Vérifie si la session existe dans la table 'sessions', sinon on la crée avec un nom par défaut
    c.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
    if c.fetchone() is None:
        default_name = f"Discussion du {datetime.datetime.now().strftime('%d/%m/%Y')}"
        c.execute("INSERT INTO sessions (session_id, device_id, name, created_at) VALUES (?, ?, ?, ?)",
                  (session_id, dev_id, default_name, datetime.datetime.now()))
                  
    conn.commit()
    conn.close()

# --- NOUVELLES FONCTIONS POUR LE MENU ---

def rename_session(session_id, new_name, device_id=None):
    """Renomme une session spécifique."""
    dev_id = device_id if device_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE sessions SET name = ? WHERE session_id = ? AND device_id = ?", 
              (new_name, session_id, dev_id))
    conn.commit()
    conn.close()

def delete_session(session_id, device_id=None):
    """Supprime une session et tous ses messages."""
    dev_id = device_id if device_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Supprime de la table messages
    cursor.execute("DELETE FROM messages WHERE session_id = ? AND device_id = ?", (session_id, dev_id))
    # Supprime de la table sessions
    cursor.execute("DELETE FROM sessions WHERE session_id = ? AND device_id = ?", (session_id, dev_id))
    
    conn.commit()
    conn.close()

# --- FONCTIONS EXISTANTES ---

def get_history(session_id, device_id=None):
    """Récupère l'historique d'une session spécifique."""
    dev_id = device_id if device_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE device_id = ? AND session_id = ? ORDER BY id ASC", (dev_id, session_id))
    rows = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

def clear_history(device_id=None):
    """Efface tout l'historique de l'appareil si besoin."""
    dev_id = device_id if device_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE device_id = ?", (dev_id,))
    cursor.execute("DELETE FROM sessions WHERE device_id = ?", (dev_id,))
    conn.commit()
    conn.close()
