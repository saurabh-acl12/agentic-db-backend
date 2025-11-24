from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv
load_dotenv()

def get_qdrant_client():
    if os.getenv("QDRANT_URL"):
        return QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
    else:
        # local docker
        return QdrantClient(host="localhost", port=6333)
