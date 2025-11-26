from chromadb import PersistentClient
from chromadb.config import Settings
import os


def get_chroma_client():
    """Return a Chromadb client.
    Uses a persistent directory defined by CHROMA_DB_PATH env variable or defaults to './chroma_db'.
    """
    db_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    client = PersistentClient(path=db_path, settings=Settings(allow_reset=True))
    return client
