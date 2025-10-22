from langchain_core.prompts import PromptTemplate

SQL_PROMPT_TEMPLATE = """
You are an expert SQL developer.
Given this database schema:
{schema}

Write a syntactically correct, optimized SQL query that answers the question:
"{question}"

Rules:
- Only return SQL code (no explanation).
- Use schema-qualified table names if needed (e.g., fac.canvas_course).
- Use meaningful joins instead of subqueries when possible.
"""

def get_sql_prompt():
    return PromptTemplate.from_template(SQL_PROMPT_TEMPLATE)
