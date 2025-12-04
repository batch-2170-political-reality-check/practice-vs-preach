from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from practicepreach import constants
from practicepreach.rag import Rag

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
    return {'party1': '**This party sucks!**',
            'party2': '*This party is kinda okay.*'}
