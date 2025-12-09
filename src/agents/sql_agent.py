from src.llm.factory import get_llm
from src.chains.query_chain import get_intent_prompt, get_sql_prompt
from src.db.connection import get_connection, get_maria_connection
from src.utils.env_loader import load_env
from src.vector.retriever import retrieve_context
from src.db.feedback import get_cached_query

import re

config = load_env()


def clean_sql_output(raw_sql: str) -> str:
    """
    Clean model output by removing markdown code fences and language tags.
    Example: ```sql SELECT * FROM table; ``` → SELECT * FROM table;
    """
    cleaned = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).replace("```sql", "").replace("```", ""), raw_sql)
    cleaned = re.sub(r"```sql|```", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    return cleaned


def is_sql_like(text: str) -> bool:
    """Quick sanity check to avoid executing junk."""
    return any(k in text.lower() for k in ["select", "from", "where"])


def get_sql_agent(schema_description: str):
    llm = get_llm()
    intent_prompt = get_intent_prompt()
    sql_prompt = get_sql_prompt()

    def process_question(question: str):
        # STEP 0 – Check semantic cache
        cached_sql = get_cached_query(question)
        if cached_sql:
            return {"sql": cached_sql, "cached": True}

        # STEP 1 – Intent validation
        intent_response = llm.invoke(intent_prompt.format(question=question))
        intent = intent_response.content.strip().upper()

        if not intent.startswith("YES"):
            return {"error": "Invalid or unclear question. Please rephrase."}

        # STEP 2 – Retrieve semantic RAG context (vector search from Qdrant)
        rag_context = retrieve_context(question)

        # STEP 3 – Build enhanced SQL prompt with context
        full_prompt = (
            sql_prompt.format(schema=schema_description, question=question)
            + "\n\n# RAG_CONTEXT (highly relevant schema fragments):\n"
            + rag_context
            + "\n# Use ONLY columns and tables found in SCHEMA or RAG_CONTEXT."
        )

        # STEP 4 – SQL generation
        sql_response = llm.invoke(full_prompt)
        raw_sql = sql_response.content

        sql = clean_sql_output(raw_sql)

        # STEP 5 – Validate SQL
        if "INVALID QUESTION" in sql.upper():
            return {"error": "Unable to interpret the question correctly."}

        if not is_sql_like(sql):
            return {"error": "Unable to generate SQL for that question."}

        return {"sql": sql, "context_used": rag_context}  # optional for debugging, remove in prod

    return process_question


def execute_sql(query: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def execute_mariadb_sql(query: str):
    conn = get_maria_connection()
    cur = conn.cursor()
    cur.execute(query)
    if cur.description:  # SELECT-like
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        return rows
    else:
        conn.commit()
        affected = cur.rowcount
        conn.close()
        return {"affected": affected}


def execute_sql_query(query: str):
    """Execute SQL query based on DB_TYPE from config."""
    db_type = config.get("DB_TYPE", "sqlite").lower()
    if db_type == "mariadb" or db_type == "mysql":
        return execute_mariadb_sql(query)
    else:
        return execute_sql(query)
