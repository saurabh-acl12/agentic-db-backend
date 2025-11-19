#!/usr/bin/env python3
"""
sqlite_full_exporter.py

Exports entire SQLite DB (schema + data + indexes + FKs + triggers + views) to MariaDB.

Usage:
  python sqlite_full_exporter.py --sqlite ./db.sqlite --host 127.0.0.1 --port 3306 --user root --password secret --database target_db [--dry-run] [--auto-increment]

Requirements:
  pip install mariadb

Notes:
- This is best-effort conversion. Review generated SQL for complex constructs.
- Run with --dry-run first to inspect SQL.
"""

import argparse
import sqlite3
import re
import mariadb
import sys
from typing import List, Tuple

BATCH_SIZE = 500


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--sqlite", required=True, help="Path to SQLite file")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=3306)
    p.add_argument("--user", default="root")
    p.add_argument("--password", required=True)
    p.add_argument("--database", required=True, help="Target MariaDB database name")
    p.add_argument("--dry-run", action="store_true", help="Print SQL instead of executing")
    p.add_argument("--auto-increment", action="store_true", help="Convert INTEGER PRIMARY KEY to AUTO_INCREMENT")
    return p.parse_args()


def load_sqlite_schema(conn: sqlite3.Connection) -> List[Tuple[str, str]]:
    """Return list of (type, name, sql) from sqlite_master in order."""
    cur = conn.cursor()
    cur.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql NOT NULL ORDER BY type DESC, name")
    return cur.fetchall()


def map_type_sqlite_to_mysql_coltype(col_type: str) -> str:
    t = (col_type or "").strip().upper()
    if not t:
        return "TEXT"
    # preserve sizes like VARCHAR(100)
    if re.search(r"(CHAR|CLOB|TEXT)", t):
        return t if "(" in t else "TEXT"
    if "INT" in t:
        return "INT"
    if "BLOB" in t:
        return "LONGBLOB"
    if "REAL" in t or "FLOA" in t or "DOUB" in t:
        return "DOUBLE"
    if "NUM" in t or "DEC" in t:
        return "DECIMAL(30,10)"
    # fallback
    return "TEXT"


def convert_create_table(sql: str, auto_inc: bool) -> str:
    """
    Convert SQLite CREATE TABLE to MariaDB. Handles:
    - column type names mapping
    - INTEGER PRIMARY KEY -> INT AUTO_INCREMENT PRIMARY KEY (if auto_inc)
    - removes WITHOUT ROWID
    - converts quoted identifiers to backticks
    """
    orig = sql.strip()
    # remove "WITHOUT ROWID"
    orig = re.sub(r"\bWITHOUT\s+ROWID\b", "", orig, flags=re.IGNORECASE)

    # simple parse: replace column types and wrap identifiers
    header_match = re.match(r"^\s*CREATE\s+TABLE\s+([^$]+)\((.*)$\s*;?\s*$", orig, flags=re.IGNORECASE | re.S)
    if not header_match:
        # fallback: replace double quotes with backticks and return
        return orig.replace('"', "`")

    tbl_name = header_match.group(1).strip()
    body = header_match.group(2).strip()

    # split columns/constraints by commas but avoid commas inside parentheses
    parts = []
    buf = ""
    depth = 0
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())

    converted_parts = []
    for part in parts:
        p = part
        # column definition likely starts with identifier
        col_match = re.match(r'^("([^"]+)"|`([^`]+)`|\'([^\']+)\'|([^\s`"\'\(]+))\s+(.*)$', p, flags=re.S)
        if col_match:
            col_name = next(g for g in col_match.groups()[1:6] if g)
            rest = col_match.group(6).strip()
            # split rest to type + constraints
            tokens = rest.split()
            col_type = tokens[0] if tokens else ""
            constraints = " ".join(tokens[1:]) if len(tokens) > 1 else ""
            mysql_type = map_type_sqlite_to_mysql_coltype(col_type)

            # handle INTEGER PRIMARY KEY -> AUTO_INCREMENT
            if (
                auto_inc
                and re.match(r"INTEGER", col_type, flags=re.I)
                and re.search(r"\bPRIMARY\s+KEY\b", rest, flags=re.I)
            ):
                converted = f"`{col_name}` INT AUTO_INCREMENT {rest.upper().replace(col_type.upper(), '').strip()}"
                # ensure PRIMARY KEY present
                if "PRIMARY KEY" not in converted.upper():
                    converted = converted + " PRIMARY KEY"
                converted_parts.append(converted)
                continue

            # keep constraints but uppercase keywords and use mapped type
            converted_parts.append(f"`{col_name}` {mysql_type} {constraints}".strip())
        else:
            # likely a table constraint like PRIMARY KEY (...) or FOREIGN KEY (...)
            # convert double quotes to backticks
            p2 = p.replace('"', "`")
            converted_parts.append(p2)
    # rebuild CREATE TABLE
    tbl_name_out = tbl_name.replace('"', "`").replace("'", "`")
    create_sql = (
        f"CREATE TABLE IF NOT EXISTS {tbl_name_out} (\n  "
        + ",\n  ".join(converted_parts)
        + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    )
    return create_sql


def convert_create_index(sql: str) -> str:
    # convert quotes to backticks; SQLite may have "CREATE INDEX name ON table(col)"
    return sql.replace('"', "`")


def convert_create_trigger(sql: str) -> str:
    return sql  # triggers syntax often compatible; minimal replace


def convert_create_view(sql: str) -> str:
    return sql.replace('"', "`")


def execute_or_print(cur, sql, dry_run):
    if dry_run:
        print("-- DRY-RUN SQL --")
        print(sql)
        print("-- END SQL --\n")
        return
    try:
        cur.execute(sql)
    except Exception as e:
        raise


def copy_table_data(sqlite_conn, mariadb_conn, table_name, dry_run):
    s_cur = sqlite_conn.cursor()
    s_cur.execute(f"PRAGMA table_info('{table_name}')")
    cols = [row[1] for row in s_cur.fetchall()]
    if not cols:
        return
    col_list = ", ".join([f"`{c}`" for c in cols])
    placeholders = ", ".join(["%s"] * len(cols))
    insert_sql = f"INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders})"
    s_cur.execute(f"SELECT {', '.join('\"'+c+'\"' for c in cols)} FROM \"{table_name}\"")
    batch = s_cur.fetchmany(BATCH_SIZE)
    total = 0
    m_cur = mariadb_conn.cursor()
    while batch:
        params = [tuple(row) for row in batch]
        if dry_run:
            for p in params[:5]:
                print("-- DRY RUN INSERT:", insert_sql, p)
            # don't print all rows in dry-run
        else:
            try:
                m_cur.executemany(insert_sql, params)
                mariadb_conn.commit()
            except Exception as e:
                mariadb_conn.rollback()
                # try row-by-row to surface bad rows
                for r in params:
                    try:
                        m_cur.execute(insert_sql, r)
                    except Exception as ex:
                        print("Failed inserting row:", r, "error:", ex)
                mariadb_conn.commit()
        total += len(batch)
        print(f"  Inserted {total} rows into {table_name}...", end="\r")
        batch = s_cur.fetchmany(BATCH_SIZE)
    print(f"\n  Finished copying data for {table_name}: {total} rows")


def main():
    args = parse_args()
    sqlite_conn = sqlite3.connect(args.sqlite)
    sqlite_conn.row_factory = sqlite3.Row

    # load sqlite schema objects
    s_cur = sqlite_conn.cursor()
    s_cur.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql NOT NULL ORDER BY type DESC, name")
    rows = s_cur.fetchall()

    # connect to MariaDB
    if not args.dry_run:
        try:
            m_conn = mariadb.connect(
                user=args.user, password=args.password, host=args.host, port=args.port, autocommit=False
            )
            m_cur = m_conn.cursor()
            # create database if not exists and use it
            m_cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{args.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            m_cur.execute(f"USE `{args.database}`;")
            m_conn.commit()
        except Exception as e:
            print("MariaDB connection error:", e)
            sys.exit(1)
    else:
        m_conn = None
        m_cur = None

    # Process in stages: tables, indexes, triggers, views (sqlite_master types: table, index, trigger, view)
    # Collect objects
    tables = []
    indexes = []
    triggers = []
    views = []
    for type_, name, tbl_name, sql in rows:
        t = type_.lower()
        entry = (name, tbl_name, sql)
        if t == "table":
            # skip sqlite_sequence (used for autoincrement)
            if name == "sqlite_sequence":
                continue
            tables.append(entry)
        elif t == "index":
            indexes.append(entry)
        elif t == "trigger":
            triggers.append(entry)
        elif t == "view":
            views.append(entry)

    # CREATE tables
    for name, tbl_name, sql in tables:
        print(f"Creating table {tbl_name}...")
        try:
            create_sql = convert_create_table(sql, args.auto_increment)
            if args.dry_run:
                print(create_sql + "\n")
            else:
                try:
                    m_cur.execute(create_sql)
                    m_conn.commit()
                except Exception as e:
                    print(f"Error creating table {tbl_name}: {e}")
                    print("Attempting to continue...")
        except Exception as e:
            print(f"Failed converting/creating table {tbl_name}: {e}")

    # COPY data for each table
    for name, tbl_name, sql in tables:
        print(f"Copying data for {tbl_name}...")
        try:
            copy_table_data(sqlite_conn, m_conn, tbl_name, args.dry_run)
        except Exception as e:
            print(f"Error copying data for {tbl_name}: {e}")

    # CREATE indexes (non-unique or unique)
    for name, tbl_name, sql in indexes:
        print(f"Creating index {name} on {tbl_name}...")
        try:
            if not sql:
                continue
            idx_sql = convert_create_index(sql)
            if args.dry_run:
                print(idx_sql + "\n")
            else:
                try:
                    m_cur.execute(idx_sql)
                    m_conn.commit()
                except Exception as e:
                    print(f"Error creating index {name}: {e}")
        except Exception as e:
            print(f"Index conversion error {name}: {e}")

    # CREATE views
    for name, tbl_name, sql in views:
        print(f"Creating view {name}...")
        try:
            view_sql = convert_create_view(sql)
            if args.dry_run:
                print(view_sql + "\n")
            else:
                try:
                    m_cur.execute(view_sql)
                    m_conn.commit()
                except Exception as e:
                    print(f"Error creating view {name}: {e}")
        except Exception as e:
            print(f"View conversion error {name}: {e}")

    # CREATE triggers
    for name, tbl_name, sql in triggers:
        print(f"Creating trigger {name}...")
        try:
            trig_sql = convert_create_trigger(sql)
            if args.dry_run:
                print(trig_sql + "\n")
            else:
                try:
                    m_cur.execute(trig_sql)
                    m_conn.commit()
                except Exception as e:
                    print(f"Error creating trigger {name}: {e}")
        except Exception as e:
            print(f"Trigger conversion error {name}: {e}")

    print("Done.")
    if m_conn:
        m_conn.close()
    sqlite_conn.close()


if __name__ == "__main__":
    main()
