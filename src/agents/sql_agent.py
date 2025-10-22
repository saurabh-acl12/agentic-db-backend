from langchain_google_genai import ChatGoogleGenerativeAI
from src.chains.query_chain import get_sql_prompt
from src.db.connection import get_connection

def get_sql_agent(schema_description: str):
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    prompt = get_sql_prompt()

    def generate_sql(question: str):
        prompt_text = prompt.format(schema=schema_description, question=question)
        response = llm.invoke(prompt_text)
        return response.content.strip()

    return generate_sql

def execute_sql(query: str):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(query)
        try:
            rows = cur.fetchall()
        except:
            rows = []
        conn.commit()
    conn.close()
    return rows
