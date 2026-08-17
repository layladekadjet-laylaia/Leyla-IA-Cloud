import sqlite3

def init_db():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT)''')
    conn.commit()
    conn.close()

def save_message(role, content):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages")
    rows = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]
