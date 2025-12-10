from src.llm.factory import get_llm
from src.chains.query_chain import get_unified_prompt
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
    unified_prompt = get_unified_prompt()

    def process_question(question: str):
        # STEP 0 – Check semantic cache
        cached_sql = get_cached_query(question)
        if cached_sql:
            return {"sql": cached_sql, "cached": True}

        # STEP 1 – Retrieve semantic RAG context
        rag_context = retrieve_context(question)

        # STEP 2 – Build unified prompt
        full_prompt = unified_prompt.format(
            schema=schema_description,
            rag_context=rag_context,
            question=question
        )

        # STEP 3 – LLM Call
        response = llm.invoke(full_prompt)
        content = response.content.strip()

        # STEP 4 – Parse JSON
        try:
            # Attempt to clean markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            import json
            data = json.loads(content)
        except Exception as e:
            return {"error": f"Failed to parse LLM response: {content}", "details": str(e)}

        intent = data.get("intent", "OFF_TOPIC")

        if intent == "SQL_GENERATION":
            sql = data.get("sql_query")
            if not sql:
                return {"error": "LLM identified SQL intent but returned no query."}

            sql = clean_sql_output(sql)
            if not is_sql_like(sql):
                return {"error": "Generated SQL is invalid."}

            return {
                "sql": sql,
                "intent": intent,
                "analysis": data.get("analysis"),
                "context_used": rag_context
            }

        elif intent == "CLARIFICATION_NEEDED":
            return {
                "error": data.get("clarification_needed", "Please clarify your question."),
                "intent": intent
            }

        else:
            # GREETING or OFF_TOPIC
            return {
                "error": "I can only answer questions about the database.",
                "intent": intent,
                "analysis": data.get("analysis")
            }

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
