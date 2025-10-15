# db.py
import sqlite3
from datetime import datetime

DB_PATH = "goals.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # users
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # goals (week_start stored as ISO Monday date)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        week_start TEXT NOT NULL,
        custom_deadline TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # tasks (linked to goal_id), track carried_over, missed, carried_from_week
    conn.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER,
        title TEXT NOT NULL,
        notes TEXT,
        due_date TEXT, -- YYYY-MM-DD
        completed INTEGER DEFAULT 0,
        carried_over INTEGER DEFAULT 0,
        missed INTEGER DEFAULT 0,
        carried_from_week TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(goal_id) REFERENCES goals(id)
    )
    """)

    conn.commit()
    return conn
