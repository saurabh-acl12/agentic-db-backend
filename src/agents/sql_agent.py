from langchain_google_genai import ChatGoogleGenerativeAI
from src.chains.query_chain import get_sql_prompt
from src.db.connection import get_connection
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

def get_sql_agent(schema_description: str):
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    prompt = get_sql_prompt()

    def generate_sql(question: str):
        prompt_text = prompt.format(schema=schema_description, question=question)
        response = llm.invoke(prompt_text)
        sql = clean_sql_output(response.content.strip())
        print("🧠 Cleaned SQL:\n", sql)
        return sql

    return generate_sql


def execute_sql(query: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]