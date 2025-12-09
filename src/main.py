from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging
from src.db.connection import get_db_schema_description
from src.agents.sql_agent import get_sql_agent, execute_sql_query
from src.db.feedback import init_feedback_db, log_query, update_rating

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="AI SQL Agent (Gemini + LangChain + FastAPI)")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Load schema once at startup
try:
    schema_description = get_db_schema_description()
except Exception as e:
    logging.error(f"Could not load DB schema: {e}")
    raise HTTPException(status_code=500, detail=str(e))
    # schema_description = ""  # fallback empty schema

# Initialize feedback DB
init_feedback_db()

# Initialize SQL agent with the (possibly empty) schema description
generate_sql = get_sql_agent(schema_description)

class FeedbackRequest(BaseModel):
    query_id: str
    rating: int

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


        # Log the query
        query_id = log_query(request.question, sql['sql'])

        result = execute_sql_query(sql['sql'])
        return {
            "sql": sql['sql'],
            "result": result,
            "query_id": query_id,
            "cached": sql.get("cached", False)
        }

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "ResourceExhausted" in error_msg:
             raise HTTPException(
                 status_code=429,
                 detail="AI Model Quota Exceeded. Please try again later or upgrade your plan."
             )
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    try:
        update_rating(request.query_id, request.rating)
        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


