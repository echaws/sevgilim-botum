import sqlite3
from datetime import datetime

DB_NAME = 'chat_stats.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (user_id INTEGER, content TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

def log_message(user_id, content):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO messages (user_id, content, timestamp) VALUES (?, ?, ?)",
              (user_id, content, datetime.now()))
    conn.commit()
    conn.close()

def get_stats(user_id=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    query = "SELECT content, timestamp FROM messages"
    params = []
    if user_id:
        query += " WHERE user_id = ?"
        params.append(user_id)
    
    c.execute(query, params)
    data = c.fetchall()
    conn.close()
    return data
