import os
import logging
from src.utils.env_loader import load_env
# We import Gemini by default as it's the primary provider
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

logger = logging.getLogger(__name__)
config = load_env()

def get_llm():
    """
    Factory function to return an LLM instance based on LLM_PROVIDER.
    Supports 'gemini' (default) and 'ollama'.
    Uses lazy imports for optional providers to avoid hard dependencies.
    """
    provider = config.get("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        # Default to gemini-flash-latest which is in the user's available list
        # and likely maps to the stable 1.5 flash model with quota
        model_name = config.get("GEMINI_MODEL", "gemini-flash-latest")
        logger.info(f"Using Gemini LLM: {model_name}")
        return ChatGoogleGenerativeAI(model=model_name, temperature=0)

    elif provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            logger.error("langchain-ollama not installed.")
            raise ImportError("Please install 'langchain-ollama' to use Ollama provider.")

        base_url = config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = config.get("OLLAMA_MODEL", "mistral")
        logger.info(f"Using Ollama LLM: {model} at {base_url}")
        return ChatOllama(
            base_url=base_url,
            model=model,
            temperature=0
        )

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

def get_embeddings():
    """
    Factory function to return an Embeddings instance based on LLM_PROVIDER.
    """
    provider = config.get("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        model_name = config.get("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
        logger.info(f"Using Gemini Embeddings: {model_name}")
        return GoogleGenerativeAIEmbeddings(model=model_name)

    elif provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError:
            logger.error("langchain-ollama not installed.")
            raise ImportError("Please install 'langchain-ollama' to use Ollama provider.")

        base_url = config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = config.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        logger.info(f"Using Ollama Embeddings: {model} at {base_url}")
        return OllamaEmbeddings(
            base_url=base_url,
            model=model
        )

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
