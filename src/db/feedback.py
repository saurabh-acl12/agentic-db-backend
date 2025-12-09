import sqlite3
import os
import uuid
import logging
from datetime import datetime
from src.utils.env_loader import load_env
from src.vector.chroma_con import get_chroma_client
from src.llm.factory import get_embeddings

from src.db.connection import get_maria_connection

logger = logging.getLogger(__name__)
config = load_env()

FEEDBACK_DB_TYPE = config.get("FEEDBACK_DB_TYPE", "sqlite").lower()
FEEDBACK_DB_PATH = config.get("FEEDBACK_DB_PATH", "./feedback.sqlite")

def get_feedback_connection():
    """Return a connection to the feedback database."""
    if FEEDBACK_DB_TYPE == "mariadb":
        return get_maria_connection()
    else:
        conn = sqlite3.connect(FEEDBACK_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_feedback_db():
    """Initialize the query_history table if it doesn't exist."""
    conn = get_feedback_connection()
    cur = conn.cursor()

    if FEEDBACK_DB_TYPE == "mariadb":
        # MariaDB Schema
        cur.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id VARCHAR(36) PRIMARY KEY,
                natural_language_query TEXT NOT NULL,
                generated_sql TEXT,
                user_rating INTEGER,
                status VARCHAR(20) DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    else:
        # SQLite Schema
        cur.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id TEXT PRIMARY KEY,
                natural_language_query TEXT NOT NULL,
                generated_sql TEXT,
                user_rating INTEGER,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    conn.commit()
    conn.close()

    # Also initialize Chromadb collection for semantic cache
    try:
        client = get_chroma_client()
        client.get_or_create_collection(name="query_cache")
    except Exception as e:
        logger.warning(f"Could not initialize Chromadb query_cache: {e}")

def log_query(question: str, generated_sql: str) -> str:
    """Log a new query and return its ID."""
    query_id = str(uuid.uuid4())
    conn = get_feedback_connection()
    cur = conn.cursor()

    if FEEDBACK_DB_TYPE == "mariadb":
        cur.execute(
            "INSERT INTO query_history (id, natural_language_query, generated_sql, status) VALUES (%s, %s, %s, %s)",
            (query_id, question, generated_sql, 'new')
        )
    else:
        cur.execute(
            "INSERT INTO query_history (id, natural_language_query, generated_sql, status) VALUES (?, ?, ?, ?)",
            (query_id, question, generated_sql, 'new')
        )

    conn.commit()
    conn.close()
    return query_id

def update_rating(query_id: str, rating: int):
    """Update the rating and status of a query."""
    status = 'rejected'
    if rating >= 9:
        status = 'verified'
    elif rating >= 7:
        status = 'pending_review'

    conn = get_feedback_connection()
    cur = conn.cursor()

    # Get the query details first
    if FEEDBACK_DB_TYPE == "mariadb":
        cur.execute("SELECT natural_language_query, generated_sql FROM query_history WHERE id = %s", (query_id,))
    else:
        cur.execute("SELECT natural_language_query, generated_sql FROM query_history WHERE id = ?", (query_id,))

    row = cur.fetchone()

    if row:
        # Handle tuple vs dict-like row
        if isinstance(row, tuple):
             question, sql = row[0], row[1]
        else:
             question, sql = row['natural_language_query'], row['generated_sql']

        # Update DB
        if FEEDBACK_DB_TYPE == "mariadb":
            cur.execute(
                "UPDATE query_history SET user_rating = %s, status = %s WHERE id = %s",
                (rating, status, query_id)
            )
        else:
            cur.execute(
                "UPDATE query_history SET user_rating = ?, status = ? WHERE id = ?",
                (rating, status, query_id)
            )
        conn.commit()

        # If verified, add to semantic cache
        if status == 'verified':
            _add_to_semantic_cache(question, sql)

    conn.close()

def _add_to_semantic_cache(question: str, sql: str):
    """Add a verified query to the Chromadb cache."""
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(name="query_cache")
        embedder = get_embeddings()
        vector = embedder.embed_query(question)

        collection.add(
            ids=[str(uuid.uuid4())],
            embeddings=[vector],
            metadatas={"sql": sql, "question": question},
            documents=[question]
        )
        logger.info(f"Added query to semantic cache: {question}")
    except Exception as e:
        logger.error(f"Failed to add to semantic cache: {e}")

def get_cached_query(question: str, threshold: float = 0.9) -> str | None:
    """Check if a similar query exists in the cache."""
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(name="query_cache")

        if collection.count() == 0:
            return None

        embedder = get_embeddings()
        vector = embedder.embed_query(question)

        results = collection.query(
            query_embeddings=[vector],
            n_results=1,
            include=["metadatas", "distances"]
        )

        if results['distances'] and results['distances'][0]:
            # Chromadb returns distance (lower is better).
            # Cosine distance: 0 = identical, 2 = opposite.
            # We want similarity > threshold.
            # Approx: similarity = 1 - distance (for normalized vectors)
            distance = results['distances'][0][0]
            if distance < (1 - threshold):
                cached_sql = results['metadatas'][0][0]['sql']
                logger.info(f"Cache hit! Distance: {distance}")
                return cached_sql

    except Exception as e:
        logger.error(f"Cache lookup failed: {e}")

    return None
