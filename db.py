# db.py
import os
import sqlite3
import logging
from typing import List

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ensure a consistent path (db next to this file)
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "goals.db")

# expected columns for tables (name -> column sql fragment)
EXPECTED_GOALS_COLUMNS = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "user_id": "INTEGER",
    "title": "TEXT NOT NULL",
    "description": "TEXT",
    "week_start": "TEXT NOT NULL",
    "custom_deadline": "TEXT",
    "category": "TEXT",                # <-- added column (your insert expects this)
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
}

EXPECTED_USERS_COLUMNS = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "name": "TEXT",
    "email": "TEXT UNIQUE",
    "password": "TEXT",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
}

EXPECTED_TASKS_COLUMNS = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "goal_id": "INTEGER",
    "title": "TEXT NOT NULL",
    "notes": "TEXT",
    "due_date": "TEXT",
    "completed": "INTEGER DEFAULT 0",
    "carried_over": "INTEGER DEFAULT 0",
    "missed": "INTEGER DEFAULT 0",
    "carried_from_week": "TEXT",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
}


def get_connection():
    """Open connection and ensure tables + missing columns exist."""
    os.makedirs(BASE_DIR, exist_ok=True)  # ensure dir exists
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
    conn.row_factory = sqlite3.Row

    # recommended pragmas
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
    except Exception as e:
        logger.warning("Failed to set sqlite pragmas: %s", e)

    # create base tables if they do not exist (these statements will not overwrite existing tables)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );""")

    conn.execute("""CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        week_start TEXT NOT NULL,
        custom_deadline TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );""")

    conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER,
        title TEXT NOT NULL,
        notes TEXT,
        due_date TEXT,
        completed INTEGER DEFAULT 0,
        carried_over INTEGER DEFAULT 0,
        missed INTEGER DEFAULT 0,
        carried_from_week TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(goal_id) REFERENCES goals(id)
    );""")

    conn.commit()

    # Ensure missing columns are added (safe ALTER TABLE ADD COLUMN)
    _ensure_table_columns(conn, "users", EXPECTED_USERS_COLUMNS)
    _ensure_table_columns(conn, "goals", EXPECTED_GOALS_COLUMNS)
    _ensure_table_columns(conn, "tasks", EXPECTED_TASKS_COLUMNS)

    # log schema for debugging
    logger.info("DB initialized at %s", DB_PATH)
    logger.info(_show_schema(conn))

    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.execute(f"PRAGMA table_info({table});")
    return [row["name"] for row in cur.fetchall()]


def _ensure_table_columns(conn: sqlite3.Connection, table: str, expected_columns: dict):
    existing = _table_columns(conn, table)
    missing = [col for col in expected_columns.keys() if col not in existing]
    if not missing:
        return

    logger.info("Table '%s' missing columns: %s", table, missing)
    for col in missing:
        # Skip adding primary key 'id' if it somehow is missing (edge case)
        if col == "id":
            logger.warning("Skipping add of primary key column 'id' for table %s", table)
            continue
        col_def = expected_columns[col]
        sql = f"ALTER TABLE {table} ADD COLUMN {col} {col_def};"
        try:
            conn.execute(sql)
            logger.info("Added column '%s' to table '%s'", col, table)
        except Exception as e:
            # log full error but continue; it's important we don't silently swallow failures
            logger.exception("Failed to add column '%s' to '%s': %s", col, table, e)
    conn.commit()


def _show_schema(conn: sqlite3.Connection) -> str:
    cur = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
    rows = cur.fetchall()
    lines = [f"{r['name']}: {r['sql']}" for r in rows]
    return "\n".join(lines)


if __name__ == "__main__":
    # quick local test: run this file and inspect logs
    c = get_connection()
    print("Schema:\n", _show_schema(c))
    c.close()
