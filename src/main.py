from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging
from src.db.connection import get_db_schema_description
from src.agents.sql_agent import get_sql_agent, execute_sql_query

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="AI SQL Agent (Gemini + LangChain + FastAPI)")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Load schema once at startup
schema_description = get_db_schema_description()
generate_sql = get_sql_agent(schema_description)

class QueryRequest(BaseModel):
    question: str
    execute: bool = True

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

@app.post("/query")
def query_db(request: QueryRequest):
    try:
        print("Question:", request.question)
        sql = generate_sql(request.question)
        print("🧠 Generated SQL:\n", sql)

        if "error" in sql:
                    raise HTTPException(status_code=400, detail=sql["error"])

        if not request.execute:
            return {"sql": sql}

        
        result = execute_sql_query(sql['sql'])
        return {"sql": sql['sql'], "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
