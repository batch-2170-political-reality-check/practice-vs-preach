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

from practicepreach import constants
from practicepreach.params import *
from practicepreach.alignment import analyze_tone_differences
from practicepreach.wahlperiode_converter import *
from practicepreach.cosine_sim import *
from practicepreach.rag import *

def _str2date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

rag = Rag()

print(f'Vectors in store:{rag.get_num_of_vectors()}')

# http://localhost:8000/summaries?topic=social&start_date=2025-07-21&end_date=2025-12-01

topic='social'
dt_start = _str2date('2024-01-01')
dt_end = _str2date('2024-12-31')
topic_long = constants.POLITICAL_TOPICS[topic]
query = f"What does the party say about {topic_long}"
print(f'{query=}')

summaries = {} # party → {'summary':"blbal", 'label':"Aligns…"}
for party in constants.PARTIES_LIST:
    (summary, label) = rag.answer(query, party, dt_start, dt_end)
    print(f'{party=}, {label=}')


