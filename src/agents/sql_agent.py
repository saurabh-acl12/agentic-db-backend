from langchain_google_genai import ChatGoogleGenerativeAI
from src.chains.query_chain import get_intent_prompt, get_sql_prompt
from src.db.connection import get_connection, get_maria_connection
import re


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
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    intent_prompt = get_intent_prompt()
    sql_prompt = get_sql_prompt()

    def process_question(question: str):
        # STEP 1 – Intent validation
        intent_response = llm.invoke(intent_prompt.format(question=question))
        intent = intent_response.content.strip().upper()

        if not intent.startswith("YES"):
            return {"error": "Invalid or unclear question. Please rephrase."}

        # STEP 2 – SQL generation
        sql_response = llm.invoke(sql_prompt.format(schema=schema_description, question=question))
        sql = clean_sql_output(sql_response.content)

        if "INVALID QUESTION" in sql or not is_sql_like(sql):
            return {"error": "Unable to generate SQL for that question."}

        return {"sql": sql}

    return process_question


def execute_sql(query: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def execute_mariadb_sql(query: str):
    conn = get_connection()
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
