import sqlite3
import mariadb
import os
import logging
from src.utils.env_loader import load_env

logger = logging.getLogger(__name__)
config = load_env()


def get_connection():
    """Return a SQLite connection to db.sqlite"""
    db_path = config.get("DB_PATH", "./db.sqlite")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # optional: makes rows dict-like
    logger.info(f"✅ Successfully connected to SQLite database at: {db_path}")
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
    conn = mariadb.connect(**params)
    logger.info(
        f"✅ Successfully connected to MariaDB database '{params['database']}' at {params['host']}:{params['port']} as user '{params['user']}'"
    )
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

    schema_description = "\n".join([f"{table}: {', '.join(cols)}" for table, cols in schema.items()])
    return schema_description


def get_mariadb_schema_description():
    """Fetch table, column info, PKs, and FKs for Gemini + RAG context."""
    conn = get_maria_connection()
    cur = conn.cursor()

    # 1. Get tables
    cur.execute(
        """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        ORDER BY TABLE_NAME;
    """
    )
    tables = [r[0] for r in cur.fetchall()]

    schema_blocks = []

    for table in tables:
        block = [f"TABLE: {table}"]

        # 2. Columns
        cur.execute(
            """
            SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_KEY
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION;
        """,
            (table,),
        )
        columns = cur.fetchall()

        block.append("COLUMNS:")
        for col, ctype, ckey in columns:
            if ckey == "PRI":
                block.append(f"  - {col} ({ctype}) [PRIMARY KEY]")
            else:
                block.append(f"  - {col} ({ctype})")

        # 3. Foreign Keys
        cur.execute(
            """
            SELECT
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND REFERENCED_TABLE_NAME IS NOT NULL;
        """,
            (table,),
        )

        fkeys = cur.fetchall()
        if fkeys:
            block.append("FOREIGN_KEYS:")
            for fk in fkeys:
                block.append(f"  - {fk[0]} → {fk[1]}.{fk[2]}")

        schema_blocks.append("\n".join(block))

    conn.close()
    return "\n\n".join(schema_blocks)


def fetch_sample_rows(limit=5):
    """Fetches sample records for each table based on DB_TYPE."""
    db_type = config.get("DB_TYPE", "sqlite").lower()
    conn = get_db_connection()
    cur = conn.cursor()

    text_blocks = []

    # Get tables based on database type
    if db_type == "mariadb" or db_type == "mysql":
        cur.execute("SHOW TABLES;")
        tables = [row[0] for row in cur.fetchall()]
    else:  # SQLite
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cur.fetchall()]

    for table in tables:
        try:
            cur.execute(f"SELECT * FROM {table} LIMIT {limit};")
            rows = cur.fetchall()

            if not rows:
                continue

            block = f"SAMPLE_ROWS: {table}\n"
            for row in rows:
                block += str(row) + "\n"

            text_blocks.append(block)

        except Exception:
            continue

    cur.close()
    conn.close()

    return "\n".join(text_blocks)


def get_db_connection():
    """Return a database connection based on DB_TYPE from config."""
    db_type = config.get("DB_TYPE", "sqlite").lower()
    if db_type == "mariadb" or db_type == "mysql":
        return get_maria_connection()
    else:
        return get_connection()


def get_db_schema_description():
    """Fetch table + column info based on DB_TYPE from config."""
    db_type = config.get("DB_TYPE", "sqlite").lower()
    if db_type == "mariadb" or db_type == "mysql":
        return get_mariadb_schema_description()
    else:
        return get_schema_description()
