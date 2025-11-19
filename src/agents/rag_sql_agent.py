from langchain_google_genai import ChatGoogleGenerativeAI
from src.chains.query_chain import get_intent_prompt, get_sql_prompt
from src.rag.vector_store import LMSVectorStore
import re


def clean_sql_output(raw_sql: str) -> str:
    """
    Clean model output by removing markdown code fences and language tags.
    """
    cleaned = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).replace("```sql", "").replace("```", ""), raw_sql)
    cleaned = re.sub(r"```sql|```", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    return cleaned


def is_sql_like(text: str) -> bool:
    """Quick sanity check to avoid executing junk."""
    return any(k in text.lower() for k in ["select", "from", "where", "insert", "update", "delete"])


def get_rag_sql_agent(schema_description: str):
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    vector_store = LMSVectorStore()
    intent_prompt = get_intent_prompt()
    sql_prompt = get_sql_prompt()

    def process_question(question: str):
        # STEP 1 – Intent validation
        intent_response = llm.invoke(intent_prompt.format(question=question))
        intent = intent_response.content.strip().upper()

        if not intent.startswith("YES"):
            return {"error": "Invalid or unclear question. Please rephrase."}

        # STEP 2 – RAG: Retrieve relevant context
        rag_context = vector_store.query(question, n_results=3)
        context_text = (
            "\n".join([f"- {doc}" for doc in rag_context]) if rag_context else "No additional context available."
        )

        # STEP 3 – Enhanced SQL generation with RAG context
        enhanced_prompt = f"""
You are an expert SQL assistant for a Learning Management System database.

Database Schema:
{schema_description}

Additional Context (Data Patterns & Business Rules):
{context_text}

Question: {question}

Based on both the schema and the additional context, write a single, syntactically correct SQL query.

===== SQL Output Rules =====
- Return only raw SQL code — no markdown fences, no explanation text
- Use lowercase_snake_case for identifiers
- Use uppercase SQL keywords
- Use explicit JOINs when possible
- Avoid SELECT *
- Use meaningful table aliases
- End the query with a semicolon

Your entire response must contain only the SQL query.
"""

        sql_response = llm.invoke(enhanced_prompt)
        sql = clean_sql_output(sql_response.content)

        if "INVALID QUESTION" in sql or not is_sql_like(sql):
            return {"error": "Unable to generate SQL for that question."}

        return {"sql": sql, "rag_context": rag_context, "context_used": bool(rag_context)}

    return process_question
