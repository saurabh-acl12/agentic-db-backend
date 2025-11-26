from src.vector.chroma_con import get_chroma_client
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embed = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

def retrieve_context(query: str, limit: int = 4):
    client = get_chroma_client()
    collection = client.get_or_create_collection(name="pmc_chunks")
    embedder = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    # Step 1: embed query
    vector = embedder.embed_query(query)

    # Step 2: call query_points correctly
    # Query Chromadb collection
    results = collection.query(
        query_embeddings=[embedder.embed_query(query)],
        n_results=limit,
        include=["documents", "metadatas"]
    )
    # Extract content from results
    chunks = []
    for doc in results.get("documents", []):
        chunks.append(doc)

    return "\n\n".join(chunks) if chunks else ""