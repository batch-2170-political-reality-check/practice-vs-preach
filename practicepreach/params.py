from dotenv import load_dotenv
import os

def require_env(*names: str):
    """Ensure required environment variables are set."""
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")

load_dotenv()

require_env("PERSIST_DIR", "SPEECHES_CSV", "SPEECHES_URLS", "BUNDESTAG_API_KEY")

PERSIST_DIR = os.environ.get("PERSIST_DIR")
SPEECHES_CSV = os.environ.get("SPEECHES_CSV")
SPEECHES_URLS = os.environ.get("SPEECHES_URLS")
BUNDESTAG_API_KEY = os.environ.get("BUNDESTAG_API_KEY")
