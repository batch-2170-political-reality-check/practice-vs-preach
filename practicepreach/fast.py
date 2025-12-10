import logging
import asyncio
from datetime import datetime, date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from datetime import datetime, date

from practicepreach import constants
from practicepreach.params import LOG_LEVEL
from practicepreach.rag import Rag

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

    app.state.rag = Rag(populate_vector_store = True)

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

@app.get("/summaries")
async def get_summaries(topic: str, start_date: str, end_date: str):
    dt_start = _str2date(start_date)
    dt_end = _str2date(end_date)

    topic_long = constants.POLITICAL_TOPICS[topic]
    query = f"What does the party say about {topic_long}"

    rag: Rag = app.state.rag

    # Process all parties in parallel
    async def process_party(party: str):
        """Process a single party (runs in thread pool)."""
        loop = asyncio.get_event_loop()
        summary, label = await loop.run_in_executor(
            None,
            rag.answer,
            query, party, dt_start, dt_end
        )
        return party, summary, label

    # Run all parties concurrently
    logger.info(f"Processing {len(constants.PARTIES_LIST)} parties in parallel")
    results = await asyncio.gather(
        *[process_party(party) for party in constants.PARTIES_LIST],
        return_exceptions=True
    )

    # Collect results
    summaries = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Party processing failed: {result}")
            continue
        party, summary, label = result
        if summary is not None and label is not None:
            summaries[party] = {'summary': summary, 'label': label}

    return summaries

def _str2date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()
