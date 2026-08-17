import sqlite3
import uuid
import hashlib

DB_NAME = 'leyla_cloud.db'

def get_device_id():
    """Génère un identifiant unique basé sur l'adresse MAC de l'appareil."""
    # uuid.getnode() récupère l'adresse MAC du matériel
    mac = str(uuid.getnode())
    # On crée un hash pour avoir un ID propre et sécurisé
    return hashlib.sha256(mac.encode()).hexdigest()[:16]

# On récupère l'ID de l'appareil une fois pour toutes au démarrage
DEVICE_ID = get_device_id()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, role TEXT, content TEXT)''')
    conn.commit()
    conn.close()

def save_message(user_id_ou_role, role_ou_content, content=None):
    """Sauvegarde en utilisant le DEVICE_ID par défaut si aucun user_id n'est spécifié."""
    if content is None:
        user_id = DEVICE_ID
        role = user_id_ou_role
        content = role_ou_content
    else:
        user_id = user_id_ou_role
        role = role_ou_content

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def get_history(user_id=None):
    """Récupère l'historique lié à l'appareil par défaut."""
    uid = user_id if user_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE user_id = ?", (uid,))
    rows = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

def get_history_by_user(user_id):
    return get_history(user_id)

def clear_history(user_id=None):
    uid = user_id if user_id else DEVICE_ID
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()
