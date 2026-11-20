import os
import sqlite3
from pathlib import Path

DATA_DIR = Path(os.getenv("AXIOM_DATA_DIR", "./data"))
DB_PATH = DATA_DIR / "axiom_sda.db"
SCHEMA_PATH = Path("backend/db/schema.sql")

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))