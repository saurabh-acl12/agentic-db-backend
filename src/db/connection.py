import sqlite3
import mariadb
import os
from src.utils.env_loader import load_env

config = load_env()


def get_connection():
    """Return a SQLite connection to db.sqlite"""
    db_path = config.get("DB_PATH", "./db.sqlite")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # optional: makes rows dict-like
    return conn


def get_maria_connection():
    """Return a MariaDB connection."""
    params = {
        "user": config.get("DB_USER", "root"),
        "password": config.get("DB_PASSWORD", ""),
        "host": config.get("DB_HOST", "127.0.0.1"),
        "port": int(config.get("DB_PORT", 3306)),
        "database": config.get("DB_NAME", "test"),
    }
    return mariadb.connect(**params)


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

    schema_description = "\n".join([f"{table}: {', '.join(cols)}" for table, cols in schema.items()])
    return schema_description


def get_mariadb_schema_description():
    """Fetch table + column info for MariaDB (for Gemini schema context)."""
    conn = get_maria_connection()
    cur = conn.cursor()
    # get tables in current database
    cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE()")
    tables = [r[0] for r in cur.fetchall()]

    schema = {}
    for t in tables:
        cur.execute(
            """
            SELECT COLUMN_NAME, COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """,
            (t,),
        )
        cols = [f"{col} ({ctype})" for col, ctype in cur.fetchall()]
        schema[t] = cols

    conn.close()
    return "\n".join([f"{table}: {', '.join(cols)}" for table, cols in schema.items()])
