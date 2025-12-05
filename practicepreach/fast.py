from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from practicepreach import constants
from practicepreach.rag import Rag

ALIGNEMENT_LABELS = [
    'Does not align well with manifesto',
    'Aligns partly with manifesto',
    'Aligns mostly with manifesto',
    'Aligns well with manifesto',
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    # e.g. connect to DB, load ML model, init client, create resources

    app.state.rag = Rag()

    print("Starting is complete.")
    yield

    # e.g. close DB connection, free resources
    print("Shutting down...")
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
def get_summary(topic: str, start_date: str, end_date: str):
    dt_start = _str2date(start_date)
    dt_end = _str2date(end_date)

    topic_long = constants.POLITICAL_TOPICS[topic]
    query = f"What does the party say about {topic_long}"

    rag: Rag = app.state.rag

    summaries = {} # party → {'summary':"blbal", 'label':"Aligns…"}
    for party in constants.PARTIES_LIST:
        import random
        label = random.choice(ALIGNEMENT_LABELS)

        summary = rag.answer(query, party, dt_start, dt_end)
        if summary is not None:
            summaries[party] = {'summary': summary, 'label': label}

    return summaries


from datetime import datetime, date
def _str2date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").date()
