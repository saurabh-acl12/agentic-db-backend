import sqlite3
import os
from src.utils.env_loader import load_env

config = load_env()

def get_connection():
    """Return a SQLite connection to db.sqlite"""
    db_path = config.get("DB_PATH", "./db.sqlite")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # optional: makes rows dict-like
    return conn


def get_schema_description():
    """Fetch table + column info for SQLite (for Gemini schema context)."""
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT m.name AS table_name,
           p.name AS column_name,
           p.type AS data_type
    FROM sqlite_master AS m
    JOIN pragma_table_info(m.name) AS p
    WHERE m.type = 'table'
    ORDER BY m.name, p.cid;
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    schema = {}
    for table, col, dtype in rows:
        schema.setdefault(table, []).append(f"{col} ({dtype})")

    schema_description = "\n".join(
        [f"{table}: {', '.join(cols)}" for table, cols in schema.items()]
    )
    return schema_description
