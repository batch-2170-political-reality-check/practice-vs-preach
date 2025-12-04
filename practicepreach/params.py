from dotenv import load_dotenv
import os

def require_env(*names: str):
    """Ensure required environment variables are set."""
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")

load_dotenv()

# TODO split params into rag and tools so we can require env vars accordingly.
#  For now we'll only require vars for the rag here to simplify deployment.
require_env("PERSIST_DIR", "SPEECHES_CSV", "GOOGLE_API_KEY") # "SPEECHES_URLS", "BUNDESTAG_API_KEY"

PERSIST_DIR = os.environ.get("PERSIST_DIR")
SPEECHES_CSV = os.environ.get("SPEECHES_CSV")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") # langchain_google_genai

SPEECHES_URLS = os.environ.get("SPEECHES_URLS")
BUNDESTAG_API_KEY = os.environ.get("BUNDESTAG_API_KEY")
SPEECHES_XML_DIR = os.environ.get("SPEECHES_XML_DIR")
