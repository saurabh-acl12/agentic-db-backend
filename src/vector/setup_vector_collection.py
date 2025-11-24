from qdrant_client.models import VectorParams, Distance
from qdrant_con import get_qdrant_client

def create_collection():
    client = get_qdrant_client()
    client.recreate_collection(
        collection_name="pmc_chunks",
        vectors_config=VectorParams(size=768, distance=Distance.COSINE)
    )
    print("Qdrant collection created!")

if __name__ == "__main__":
    create_collection()
