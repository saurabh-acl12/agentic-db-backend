from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.db.connection import get_schema_description
from src.agents.sql_agent import get_sql_agent, execute_sql

app = FastAPI(title="AI SQL Agent (Gemini + LangChain + FastAPI)")

# Load schema once at startup
schema_description = get_schema_description()
generate_sql = get_sql_agent(schema_description)

class QueryRequest(BaseModel):
    question: str
    execute: bool = True

@app.post("/query")
def query_db(request: QueryRequest):
    try:
        sql = generate_sql(request.question)
        print("🧠 Generated SQL:\n", sql)

        if not request.execute:
            return {"sql": sql}

        
        return {"sql": sql}  # Return top 20 rows

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
