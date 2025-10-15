"""
Simple SQLite connection helper and schema initialization.
Provides get_db() for use by services.
"""

import sqlite3
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()  # loads .env from project root

DB_PATH = os.getenv("DATABASE_URL", "./eventecho.db")
DB_PATH = str(Path(DB_PATH).resolve())

def get_db():
    """
    Return a new sqlite3.Connection with row access by name.
    Caller is responsible for closing the connection.
    """
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(schema_path: str):
    """
    Initialize or migrate database using provided SQL schema file path.
    """
    with get_db() as conn, open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())