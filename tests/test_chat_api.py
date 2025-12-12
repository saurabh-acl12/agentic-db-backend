import tempfile

from chromadb import PersistentClient
from fastapi.testclient import TestClient

from src import main
from src.vector.memory_store import ChatMemoryStore


class FakeEmbedder:
    def embed_query(self, _text: str):
        return [0.1, 0.2, 0.3, 0.4]


def fake_generate_sql(question: str, history_context: str = ""):
    return {"sql": "SELECT 1"}


def test_chat_message_flow(monkeypatch, tmp_path):
    # Fresh memory store to avoid mixing with real embeddings
    temp_store = ChatMemoryStore(
        client=PersistentClient(path=str(tmp_path)), embedder=FakeEmbedder()
    )

    monkeypatch.setattr(main, "memory_store", temp_store)
    monkeypatch.setattr(main, "generate_sql", fake_generate_sql)
    monkeypatch.setattr(main, "execute_sql_query", lambda sql: [{"value": 1}])

    client = TestClient(main.app)

    response = client.post("/chat/message", json={"message": "Hello", "execute": True})
    assert response.status_code == 200

    payload = response.json()
    assert payload["sql"] == "SELECT 1"
    assert payload["result"] == [{"value": 1}]
    assert payload["session_id"]

    # History endpoint should now return a record
    hist = client.get(f"/chat/{payload['session_id']}/history")
    assert hist.status_code == 200
    assert len(hist.json().get("history", [])) >= 1

