import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging
from src.db.connection import get_db_schema_description
from src.agents.sql_agent import get_sql_agent, execute_sql_query
from src.vector.memory_store import memory_store

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
    logging.warning(f"Could not load DB schema: {e}")
    schema_description = ""  # fallback empty schema

# Initialize SQL agent with the (possibly empty) schema description
generate_sql = get_sql_agent(schema_description)

class QueryRequest(BaseModel):
    question: str
    execute: bool = True


class ChatMessageRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
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


@app.post("/chat/start")
def start_chat():
    """Create a new chat session id."""
    return {"session_id": str(uuid.uuid4())}


@app.get("/chat/{session_id}/history")
def chat_history(session_id: str, limit: int = 20):
    """Return recent turns for a given session."""
    turns = memory_store.get_recent_turns(session_id, limit=limit)
    return {"session_id": session_id, "history": turns}


@app.post("/chat/message")
def chat_message(request: ChatMessageRequest):
    """
    Chat endpoint: generate SQL, optionally execute, and persist memory.
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())

        history_context = memory_store.build_context(session_id, request.message)
        sql_payload = generate_sql(request.message, history_context=history_context)

        if "error" in sql_payload:
            raise HTTPException(status_code=400, detail=sql_payload["error"])

        sql = sql_payload.get("sql")
        result = []

        if request.execute:
            result = execute_sql_query(sql)

        memory_store.add_turn(
            session_id=session_id,
            question=request.message,
            sql=sql,
            result=result,
        )

        return {
            "session_id": session_id,
            "sql": sql,
            "result": result,
            "context": history_context,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
