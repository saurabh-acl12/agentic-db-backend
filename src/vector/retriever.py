from src.vector.qdrant_con import get_qdrant_client
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embed = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

def retrieve_context(query: str, limit: int = 4):
    client = get_qdrant_client()
    embedder = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    # Step 1: embed query
    vector = embedder.embed_query(query)

    # Step 2: call query_points correctly
    results = client.query_points(
        collection_name="pmc_chunks",
        query=vector,            # <-- CORRECT (your version supports this)
        limit=limit,
        with_payload=True,
        with_vectors=False
    )

    # Step 3: convert to text blocks
    chunks = [
        point.payload.get("content", "")
        for point in results.points
        if "content" in point.payload
    ]

    return "\n\n".join(chunks) if chunks else ""