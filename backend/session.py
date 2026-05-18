import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "sessions.db")

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (session_id TEXT, question TEXT, answer TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

_init_db()

def get_session_history(session_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT question, answer FROM sessions WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
        rows = c.fetchall()
        conn.close()
        return [{"question": r[0], "answer": r[1]} for r in rows]
    except Exception as e:
        print(f"Error reading session history: {e}")
        return []

def add_to_session(session_id, question, answer):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO sessions (session_id, question, answer) VALUES (?, ?, ?)", (session_id, question, answer))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error adding to session: {e}")