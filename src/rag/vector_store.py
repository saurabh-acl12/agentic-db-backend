import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.utils.env_loader import load_env
import logging

logger = logging.getLogger(__name__)
config = load_env()


class LMSVectorStore:
    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        self.client = chromadb.PersistentClient(path="./chroma_lms")
        self.collection = self.client.get_or_create_collection(
            name="lms_knowledge", metadata={"description": "LMS business rules and data patterns"}
        )

    def add_documents(self, documents: list, metadata: list = None):
        """Add knowledge documents to vector store"""
        if not documents:
            return

        ids = [f"doc_{i}" for i in range(len(documents))]

        if metadata is None:
            metadata = [{}] * len(documents)

        self.collection.add(documents=documents, metadatas=metadata, ids=ids)
        logger.info(f"Added {len(documents)} documents to vector store")

    def query(self, query: str, n_results: int = 3) -> list:
        """Retrieve relevant context for a query"""
        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)
            return results["documents"][0] if results["documents"] else []
        except Exception as e:
            logger.error(f"Error querying vector store: {e}")
            return []
