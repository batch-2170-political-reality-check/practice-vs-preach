import json
import logging
import asyncio
from datetime import datetime, date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from practicepreach import constants
from practicepreach.params import LOG_LEVEL
from practicepreach.rag import Rag

TOPS_JSON = Path("data/tops.json")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    # e.g. connect to DB, load ML model, init client, create resources

    app.state.rag = Rag()

    # Update ChromaDB with recent speeches in the background so the API is
    # immediately available while new data is being embedded.
    # threading.Thread(
    #     target=run_update,
    #     args=(app.state.rag,),
    #     daemon=True,
    #     name="speech-updater",
    # ).start()

    logger.info("Starting is complete.")
    yield

    # e.g. close DB connection, free resources
    logger.info("Shutting down...")
    app.state.rag.shutdown()

app = FastAPI(lifespan=lifespan)

# Allowing all middleware is optional, but good practice for dev purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def root():
    return {'greeting': 'PracticePreach FastAPI is running!'}

@app.get("/parameters")
def get_parameters():
    return {
        'political_topics': constants.POLITICAL_TOPICS,
        'bundestag_wahlperiode': constants.BUNDESTAG_WAHLPERIODE,
    }

def _load_tops_with_active_keys(rag: Rag):
    if not TOPS_JSON.exists():
        raise HTTPException(status_code=404, detail="tops.json not found — run build_tops_json.py first")
    tops = json.loads(TOPS_JSON.read_text())
    col = rag.vector_store._collection
    result = col.get(where={"type": {"$eq": "speech"}}, include=["metadatas"])
    active_keys = {m["top_key"] for m in result["metadatas"] if m.get("top_key")}

    # Derive PDF URL from any speech ID (format: ID{wp}{session_padded}...)
    pdf_url = ""
    for m in result["metadatas"]:
        sid = m.get("id", "")
        if sid.startswith("ID") and len(sid) >= 8:
            wp = sid[2:4]
            session = sid[4:6].zfill(3)
            pdf_url = f"https://dserver.bundestag.de/btp/{wp}/{wp}{session}.pdf"
            break

    return tops, active_keys, pdf_url

@app.get("/topics")
def get_topics():
    rag: Rag = app.state.rag
    tops, active_keys, _ = _load_tops_with_active_keys(rag)
    return sorted(
        [t for t in tops.values() if t["top_key"] in active_keys],
        key=lambda x: (x["date"], x["top_id"]),
    )

@app.get("/all_topics")
def get_all_topics():
    rag: Rag = app.state.rag
    tops, active_keys, pdf_url = _load_tops_with_active_keys(rag)
    result = []
    for t in sorted(tops.values(), key=lambda x: (x["date"], x["top_id"])):
        result.append({**t, "active": t["top_key"] in active_keys, "pdf_url": pdf_url})
    return result

@app.get("/summaries")
async def get_summaries(top_key: str):
    rag: Rag = app.state.rag

    async def process_party(party: str):
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(
            None, rag.summarize_by_top_key, top_key, party
        )
        return party, summary

    logger.info(f"Summarising top_key={top_key} for {len(constants.PARTIES_LIST)} parties")
    results = await asyncio.gather(
        *[process_party(party) for party in constants.PARTIES_LIST],
        return_exceptions=True,
    )

    summaries = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Party processing failed: {result}")
            continue
        party, summary = result
        if summary is not None:
            summaries[party] = {"summary": summary, "label": None}

    return summaries

def _str2date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()
