from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging
from src.db.connection import get_db_schema_description
from src.agents.rag_sql_agent import get_rag_sql_agent  # Updated import
from src.rag.knowledge_builder import KnowledgeBuilder
from src.agents.sql_agent import execute_sql_query

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = FastAPI(title="AI SQL Agent with RAG (Gemini + LangChain + FastAPI)")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Global variables
schema_description = None
generate_sql = None


@app.on_event("startup")
async def startup_event():
    """Initialize RAG knowledge base and SQL agent on startup"""
    global schema_description, generate_sql

    # Load schema
    schema_description = get_db_schema_description()
    logging.info("✅ Database schema loaded")

    # Initialize RAG knowledge base
    try:
        knowledge_builder = KnowledgeBuilder()
        # Build knowledge from existing data patterns
        knowledge_builder.build_data_patterns_knowledge()
        # Add business rules
        knowledge_builder.add_business_rules()
        # Add query examples
        knowledge_builder.add_query_examples()
        logging.info("✅ RAG knowledge base initialized")
    except Exception as e:
        logging.warning(f"⚠️  RAG knowledge base initialization failed: {e}")
        logging.info("ℹ️  Continuing without RAG context")

    # Create SQL agent (with RAG if available)
    generate_sql = get_rag_sql_agent(schema_description)
    logging.info("✅ SQL Agent with RAG initialized")


class QueryRequest(BaseModel):
    question: str
    execute: bool = True


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.post("/query")
def query_db(request: QueryRequest):
    try:
        if not generate_sql:
            raise HTTPException(status_code=503, detail="Service not ready")

        print("Question:", request.question)
        result = generate_sql(request.question)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        # Log RAG context for debugging
        if result.get("rag_context"):
            print("📚 RAG Context Used:")
            for ctx in result["rag_context"]:
                print(f"  - {ctx}")

        if not request.execute:
            return {
                "sql": result["sql"],
                "rag_used": result.get("context_used", False),
                "rag_context": result.get("rag_context", []),
            }

        execution_result = execute_sql_query(result["sql"])
        return {"sql": result["sql"], "result": execution_result, "rag_used": result.get("context_used", False)}

    except Exception as e:
        logging.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# RAG monitoring endpoints
@app.get("/rag/status")
def get_rag_status():
    """Check RAG knowledge base status"""
    try:
        from src.rag.vector_store import LMSVectorStore

        vector_store = LMSVectorStore()
        count = vector_store.collection.count()
        return {"status": "active", "document_count": count, "collection": "lms_knowledge"}
    except Exception as e:
        return {"status": "inactive", "error": str(e)}


@app.get("/rag/context")
def get_rag_context(question: str):
    """Debug endpoint to see what RAG context would be retrieved"""
    try:
        from src.rag.vector_store import LMSVectorStore

        vector_store = LMSVectorStore()
        context = vector_store.query(question)
        return {"question": question, "retrieved_context": context, "context_count": len(context)}
    except Exception as e:
        return {"error": str(e)}
