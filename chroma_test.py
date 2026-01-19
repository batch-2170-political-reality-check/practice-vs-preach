import logging, http.client as http_client

import pandas as pd

import time

from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_classic import hub
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import NLTKTextSplitter
from langchain_core.documents import Document

from datetime import datetime

from practicepreach.constants import *
from practicepreach.params import *
from practicepreach.alignment import analyze_tone_differences
from practicepreach.wahlperiode_converter import *
from practicepreach.cosine_sim import *

def _str2date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    credentials=None  # Explicitly disable ADC
)

model = init_chat_model("google_genai:gemini-2.5-flash-lite")

prompt_template = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Use the following context to answer the question. Use maximum 7 sentences. Use specific terms. Highlight important ones."),
            ("human", """Context: {context}  Question: {question}""")
        ])

vector_store = Chroma(
    collection_name="political_collection",
    persist_directory=PERSIST_DIR,
    embedding_function=embeddings,
)

print(f'{vector_store._collection.count()}')

#topic_long = constants.POLITICAL_TOPICS[topic]
#query = f"What does the party say about {topic_long}"

#http://localhost:8000/summaries?topic=social&start_date=2025-07-21&end_date=2025-12-01

party = 'SPD'
doctype = 'speech'
start_date = _str2date('2025-07-21')
end_date = _str2date('2025-12-01')
start_date_int = int(start_date.strftime("%Y%m%d"))
end_date_int =int(end_date.strftime("%Y%m%d"))

filter={'$and': [
    {'party': {'$eq': party}},
    {'date': {'$gte': start_date_int}},
    {'date': {'$lte': end_date_int}},
    {'type': {'$eq': doctype}},
]}

query0 = 'What does the party say about Social Security & Welfare / Pensions'
query1 = 'What did the speaker say about climate policy?'

docs = vector_store.similarity_search_with_score(query0,k=5, filter=filter)
#docs = vector_store.similarity_search(query0,k=5)

print(docs)
