import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.vector.chroma_con import get_chroma_client


def _utc_timestamp() -> str:
    """Return an ISO8601 UTC timestamp suitable for sorting."""
    return datetime.utcnow().isoformat() + "Z"


def _safe_text(value: Any, limit: int = 1200) -> str:
    """Convert values (including SQL results) to a bounded string for storage."""
    try:
        text = json.dumps(value, default=str)
    except Exception:
        text = str(value)
    if len(text) > limit:
        return text[:limit] + "..."
    return text


class ChatMemoryStore:
    """
    Simple conversation memory built on Chroma.

    Stores each turn (question, generated SQL, execution result) as a document.
    Retrieval combines semantic search + the most recent turns for grounding.
    """

    def __init__(
        self,
        client=None,
        embedder: Optional[GoogleGenerativeAIEmbeddings] = None,
        collection_name: str = "chat_memory",
    ):
        self.client = client or get_chroma_client()
        self.embedder = embedder or GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004"
        )
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_turn(
        self,
        session_id: str,
        question: str,
        sql: Optional[str],
        result: Any,
    ) -> str:
        """
        Store a single conversational turn and return its id.
        """
        turn_id = str(uuid.uuid4())
        created_at = _utc_timestamp()

        doc = (
            f"session:{session_id}\n"
            f"question:{question}\n"
            f"sql:{sql or ''}\n"
            f"result:{_safe_text(result)}\n"
            f"timestamp:{created_at}"
        )

        metadata = {
            "session_id": session_id,
            "question": question,
            "sql": sql,
            "created_at": created_at,
        }

        embedding = self.embedder.embed_query(doc)

        self.collection.add(
            ids=[turn_id],
            embeddings=[embedding],
            documents=[doc],
            metadatas=[metadata],
        )

        return turn_id

    def get_recent_turns(
        self, session_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent turns (sorted by created_at desc).
        """
        data = self.collection.get(where={"session_id": session_id}, include=["documents", "metadatas"])
        ids = data.get("ids", []) or []
        docs = data.get("documents", []) or []
        metas = data.get("metadatas", []) or []

        turns = []
        for turn_id, doc, meta in zip(ids, docs, metas):
            if not meta:
                continue
            turns.append(
                {
                    "id": turn_id,
                    "question": meta.get("question", ""),
                    "sql": meta.get("sql"),
                    "document": doc,
                    "created_at": meta.get("created_at"),
                }
            )

        turns.sort(key=lambda t: t.get("created_at") or "", reverse=True)
        return turns[:limit]

    def search_relevant(
        self, session_id: str, query: str, limit: int = 4
    ) -> List[str]:
        """
        Semantic search over a session's history to surface relevant snippets.
        """
        embedding = self.embedder.embed_query(query)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=limit,
            where={"session_id": session_id},
            include=["documents"],
        )
        documents = results.get("documents") or []
        if not documents:
            return []
        # Chroma returns a list of lists
        flat = []
        for doc_list in documents:
            if doc_list:
                flat.extend(doc_list)
        return flat

    def build_context(self, session_id: str, query: str) -> str:
        """
        Compose prompt-ready context using semantic hits + most recent turns.
        """
        semantic_hits = self.search_relevant(session_id, query, limit=4)
        recent_turns = self.get_recent_turns(session_id, limit=4)
        recent_docs = [t["document"] for t in recent_turns]

        combined = semantic_hits + recent_docs
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for doc in combined:
            if doc in seen:
                continue
            seen.add(doc)
            unique.append(doc)

        return "\n\n".join(unique)


# Default store instance used by the app
memory_store = ChatMemoryStore()

