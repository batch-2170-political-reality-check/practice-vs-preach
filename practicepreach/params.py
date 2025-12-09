from dotenv import load_dotenv
import os
import gcsfs
import pandas as pd

def require_env(*names: str):
    """Ensure required environment variables are set."""
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")

load_dotenv()

# Variables required for the Rag

require_env("DATA_CSV", "GS_URI", "GOOGLE_API_KEY")

# Chroma configuration - either embedded or external
PERSIST_DIR = os.environ.get("PERSIST_DIR")  # For embedded Chroma
CHROMADB_HOST = os.environ.get("CHROMADB_HOST")  # For external ChromaDB
CHROMADB_PORT = os.environ.get("CHROMADB_PORT", "8000")  # Default port

# Other required vars
DATA_CSV = os.environ.get("DATA_CSV")
GS_URI = os.environ.get("GS_URI")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") # langchain_google_genai

# Determine mode
USE_EXTERNAL_CHROMA = bool(CHROMADB_HOST)
if not USE_EXTERNAL_CHROMA and not PERSIST_DIR:
    raise RuntimeError("Either PERSIST_DIR (embedded) or CHROMADB_HOST (external) must be set")

def is_cloud_run() -> bool:
    return "K_SERVICE" in os.environ

def load_csv_from_gcs(path: str) -> pd.DataFrame:
    fs = gcsfs.GCSFileSystem()
    with fs.open(path, 'r') as f:
        return pd.read_csv(f)

if is_cloud_run():
    # production environment
    if PERSIST_DIR:  # Only modify if using embedded mode
        PERSIST_DIR = os.path.join(GS_URI, PERSIST_DIR)
    DATA_CSV = os.path.join(GS_URI, DATA_CSV)

if USE_EXTERNAL_CHROMA:
    print(f"Using external ChromaDB at {CHROMADB_HOST}:{CHROMADB_PORT}")
else:
    print(f"Using embedded Chroma storage: {PERSIST_DIR}")
