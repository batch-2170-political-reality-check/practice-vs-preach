from dotenv import load_dotenv
import os

def require_env(*names: str):
    """Ensure required environment variables are set."""
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")

load_dotenv()

# Variables required for the Rag

require_env("PERSIST_DIR", "SPEECHES_CSV", "MANIFESTOS_CSV","GOOGLE_API_KEY") 

PERSIST_DIR = os.environ.get("PERSIST_DIR")
SPEECHES_CSV = os.environ.get("SPEECHES_CSV")
MANIFESTOS_CSV=os.environ.get("MANIFESTOS_CSV")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") # langchain_google_genai
