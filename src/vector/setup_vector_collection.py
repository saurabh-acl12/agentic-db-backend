# Chromadb does not require VectorParams; we'll use its own collection API
from src.vector.chroma_con import get_chroma_client

def create_collection():
    client = get_chroma_client()
    # Create or get collection; Chromadb creates if not exists
    client.get_or_create_collection(name="pmc_chunks")
    print("Chromadb collection ready!")

if __name__ == "__main__":
    create_collection()
