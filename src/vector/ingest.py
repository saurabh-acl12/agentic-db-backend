import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
# Chromadb does not use PointStruct; embeddings will be stored directly

from src.vector.chroma_con import get_chroma_client
from src.db.connection import get_db_schema_description, fetch_sample_rows

def ingest():
    # Initialize Chromadb client and collection
    client = get_chroma_client()
    collection = client.get_or_create_collection(name="pmc_chunks")

    # Gather schema and sample data
    schema_text = get_db_schema_description()
    sample_text = fetch_sample_rows()

    documents = [
        "SCHEMA:\n" + schema_text,
        "SAMPLES:\n" + sample_text,
    ]

    # Split documents into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = []
    for doc in documents:
        chunks.extend(splitter.split_text(doc))

    embedder = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    # Prepare data for Chromadb
    ids = []
    embeddings = []
    metadatas = []
    docs = []
    for chunk in chunks:
        ids.append(str(uuid.uuid4()))
        embeddings.append(embedder.embed_query(chunk))
        metadatas.append({"content": chunk})
        docs.append(chunk)

    # Add to collection
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=docs
    )

    print("Database → Chromadb ingestion completed successfully!")

if __name__ == "__main__":
    ingest()
