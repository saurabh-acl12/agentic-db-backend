import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client.models import PointStruct

from qdrant_con import get_qdrant_client
from src.db.connection import get_db_schema_description, fetch_sample_rows

def ingest():
    client = get_qdrant_client()

    schema_text = get_db_schema_description()
    sample_text = fetch_sample_rows()

    
    documents = [
        "SCHEMA:\n" + schema_text,
        "SAMPLES:\n" + sample_text,
    ]

    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = []
    for doc in documents:
        chunks.extend(splitter.split_text(doc))

    embedder = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    points = []
    for chunk in chunks:
        vector = embedder.embed_query(chunk)
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={"content": chunk}
            )
        )

    client.upsert(
        collection_name="pmc_chunks",
        points=points
    )

    print("Database → Qdrant ingestion completed successfully!")

if __name__ == "__main__":
    ingest()
