import os
from dotenv import load_dotenv

def load_env():
    load_dotenv()
    config = {
        # LLM Configuration
        "USE_OLLAMA": os.getenv("USE_OLLAMA", "false").lower(),
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "gemma3:4b"),
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        
        # Database Configuration
        "DB_TYPE": os.getenv("DB_TYPE", "sqlite").lower(),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_PORT": os.getenv("DB_PORT", "3306"),
        "DB_PATH": os.getenv("DB_PATH"),
    }
    return config
