import os
from dotenv import load_dotenv

def load_env():
    load_dotenv()
    config = {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "DB_TYPE": os.getenv("DB_TYPE", "sqlite").lower(),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_PORT": os.getenv("DB_PORT", "3306"),
        "DB_PATH": os.getenv("DB_PATH"),
        "LLM_PROVIDER": os.getenv("LLM_PROVIDER", "gemini").lower(),
        "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "mistral"),
        "OLLAMA_EMBEDDING_MODEL": os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    }
    return config
