import os
from dotenv import load_dotenv

def load_env():
    load_dotenv()
    config = {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_PORT": os.getenv("DB_PORT", "5432"),
    }
    return config
