import tempfile

from chromadb import PersistentClient

from src.vector.memory_store import ChatMemoryStore


class FakeEmbedder:
    def embed_query(self, _text: str):
        # Fixed-size vector so Chroma accepts the embedding
        return [0.1, 0.2, 0.3, 0.4]


def test_add_and_retrieve_turns():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ChatMemoryStore(
            client=PersistentClient(path=tmpdir), embedder=FakeEmbedder()
        )

        session_id = "s1"
        store.add_turn(session_id, "first question", "SELECT 1", [{"a": 1}])
        store.add_turn(session_id, "second question", "SELECT 2", [{"b": 2}])

        turns = store.get_recent_turns(session_id, limit=5)

        assert len(turns) == 2
        assert turns[0]["question"] == "second question"  # newest first

        context = store.build_context(session_id, "second")
        assert "first question" in context

