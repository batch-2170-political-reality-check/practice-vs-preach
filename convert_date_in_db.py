import os
from datetime import datetime
from math import ceil

from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_classic import hub
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import NLTKTextSplitter
from langchain_core.documents import Document

def convert_date_eu_to_int(date_str: str) -> int:
    """Convert 'DD.MM.YYYY' → 20251127."""
    dt = datetime.strptime(date_str, "%d.%m.%Y")
    return int(dt.strftime("%Y%m%d"))

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    credentials=None  # Explicitly disable ADC
)

PERSIST_DIR = os.getenv("PERSIST_DIR")

# Load existing vector store
vectordb = Chroma(
    collection_name="political_collection",
    persist_directory=PERSIST_DIR,
    embedding_function=embeddings,  # same embeddings you used to create it
)

BATCH_SIZE = 5000  # must be <= 5461

vectordb = Chroma(
    collection_name="political_collection",
    persist_directory=PERSIST_DIR,
    embedding_function=embeddings,
)

# Fetch only what we need
docs = vectordb.get(include=["metadatas"])

ids = docs["ids"]
metadatas = docs["metadatas"]

total = len(ids)
batches = ceil(total / BATCH_SIZE)

vectors_converted = 0

for i in range(batches):
    start = i * BATCH_SIZE
    end = start + BATCH_SIZE

    batch_ids = ids[start:end]
    batch_metas = []

    for md in metadatas[start:end]:
        md = md.copy()
        date_str = md.get("date")

        # Guard: skip already-converted values
        if isinstance(date_str, str):
            md["date"] = convert_date_eu_to_int(date_str)
            vectors_converted += 1
        batch_metas.append(md)

    vectordb._collection.update(
        ids=batch_ids,
        metadatas=batch_metas,
    )

    print(f"Updated batch {i + 1}/{batches}")
print(f'Converted {vectors_converted} vectors')

