import os
import logging
from src.utils.env_loader import load_env
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_ollama import ChatOllama, OllamaEmbeddings

logger = logging.getLogger(__name__)
config = load_env()

def get_llm():
    """
    Factory function to return an LLM instance based on LLM_PROVIDER env var.
    Defaults to 'gemini'.
    """
    provider = config.get("LLM_PROVIDER", "gemini").lower()

    if provider == "ollama":
        base_url = config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = config.get("OLLAMA_MODEL", "mistral")
        logger.info(f"Using Ollama LLM: {model} at {base_url}")
        return ChatOllama(
            base_url=base_url,
            model=model,
            temperature=0
        )
    else:
        # Default to Gemini
        logger.info("Using Gemini LLM")
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash")

def get_embeddings():
    """
    Factory function to return an Embeddings instance based on LLM_PROVIDER env var.
    Defaults to 'gemini'.
    """
    provider = config.get("LLM_PROVIDER", "gemini").lower()

    if provider == "ollama":
        base_url = config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = config.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        logger.info(f"Using Ollama Embeddings: {model} at {base_url}")
        return OllamaEmbeddings(
            base_url=base_url,
            model=model
        )
    else:
        # Default to Gemini
        logger.info("Using Gemini Embeddings")
        return GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
