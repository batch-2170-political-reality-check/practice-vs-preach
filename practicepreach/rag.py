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

# Debug http calls.
# http_client.HTTPConnection.debuglevel = 0
# for name in ("mlflow", "urllib3", "requests"):
#     logging.getLogger(name).setLevel(logging.DEBUG)
#     logging.getLogger(name).addHandler(logging.StreamHandler())

logger = logging.getLogger(__name__)

class Rag:
    def __init__(self, populate_vector_store: bool = False):
        # Debugging
        if GOOGLE_API_KEY:
            masked_api_key = '*' * len(GOOGLE_API_KEY)
            logger.info(f"Masked API Key: {masked_api_key}")
        else:
            logger.info("API Key not found in environment variables.")

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            credentials=None  # Explicitly disable ADC
        )
        self.model = init_chat_model("google_genai:gemini-2.5-flash-lite")

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Use the following context to answer the question. Use maximum 7 sentences. Use specific terms. Highlight important ones."),
            ("human", """Context: {context}  Question: {question}""")
        ])

        self.vector_store = Chroma(
            collection_name="political_collection",
            persist_directory=PERSIST_DIR,
            embedding_function=self.embeddings,
        )

        num_of_stored = self.vector_store._collection.count()

        logger.info(f"Number of vectors stored at instance startup: {num_of_stored}")

        if num_of_stored == 0 and populate_vector_store:

            num_of_chunks_speech = self.add_to_vector_store(DATA_CSV)
            logger.info(f"Embedded {num_of_chunks_speech} chunks into the vector store.")

        else:

            logger.info(f"Vector store already has {num_of_stored} vectores. Skipping embedding.")

    def get_num_of_vectors(self) -> int:
        """Get the number of vectors stored in the vector store."""
        return self.vector_store._collection.count()

    def add_to_vector_store(self, data_source):
        """Add new documents to the vector store from CSV file"""
        logger.info(f'Processing file: {data_source}')
        loader = CSVLoader(file_path=data_source, metadata_columns=['date','id','party','type'])
        data = loader.load()

        for doc in data:
            date_str = doc.metadata["date"]   # e.g. "27.11.2025"
        doc.metadata["date"] = self.convert_date_eu_to_int(date_str)

        text_splitter = NLTKTextSplitter(
            chunk_size=500,
            chunk_overlap=200
        )
        num_of_chunks = self.embed_and_store(data, text_splitter)
        return num_of_chunks

    def convert_date_eu_to_int(self,date_str: str) -> int:
        """Convert 'DD.MM.YYYY' → 20251127."""
        dt = datetime.strptime(date_str, "%d.%m.%Y")
        return int(dt.strftime("%Y%m%d"))


    def embed_and_store(self, doc, text_splitter, batch_size=200):
        """Split documents into chunks and store them in a vector store."""
        # Split the pages into chunks
        all_splits = text_splitter.split_documents(doc)
        num_of_splits = len(all_splits)
        logger.info(f"Total chunks to embed: {num_of_splits}")

        # Add the chunks to the vector store in batches
        for i in range(0, num_of_splits, batch_size):
            batch = all_splits[i:i + batch_size]
            self.vector_store.add_documents(documents=batch)

        return num_of_splits

    def retrieve_topic_chunks(
            self,
            query, party,
            start_date:datetime, end_date:datetime,
            doctype: str,
    ):
        start_date_int = int(start_date.strftime("%Y%m%d"))
        end_date_int =int(end_date.strftime("%Y%m%d"))

        #ToDo: !!once the csv had a populated type column, add it here to make it queriable
        filter={'$and': [
            {'party': {'$eq': party}},
            {'date': {'$gte':start_date_int}},
            {'date': {'$lte': end_date_int}},
            {'type': {'$eq': doctype}},
        ]}

        # Retrieve similar documents from the vector store
        retrieved_docs = self.vector_store.similarity_search_with_score(query,k=50, filter=filter)

        return retrieved_docs


    def answer(self, query, party, start_date:datetime, end_date:datetime, prompt_template=None):
        """Answer a query using the vector store and the language model."""
        
        speech_docs = self.retrieve_topic_chunks(query, party, start_date,
                                                 end_date, doctype='speech')
        manifesto_docs = self.retrieve_topic_chunks(query, party,
                                                    convert_to_wp_start(start_date),
                                                    convert_to_wp_start(end_date),
                                                    doctype='manifesto')
        logger.info(f"speech → {speech_docs[:5]}")
        logger.info(f"manifesto → {manifesto_docs[:5]}")
        
        # Score
        # Cosine Similarity between speech and query and manifesto and query
        # TODO: Decide if we want to use it in combination with Cosine Similarity between speech and manifesto

        speech_docs_len = len(speech_docs)
        manifesto_docs_len = len(manifesto_docs)

        avg_score_speech = sum(score for _, score in speech_docs) / speech_docs_len \
                if speech_docs_len else 0
        avg_score_manifesto = sum(score for _, score in manifesto_docs) / manifesto_docs_len \
                if manifesto_docs_len else 0

        sim_speech = 1- avg_score_speech
        sim_mani = 1 - avg_score_manifesto
        diff = abs(sim_speech - sim_mani)
        align_score = 1 - diff
        # Cosine Similarity between speech and manifesto
        cos = content_alignment_from_store(self.vector_store,speech_docs,manifesto_docs ) \
                if speech_docs_len and avg_score_manifesto else NOT_ENOUGHT_DATA_FOR_SCORE

        # Summary
        speech_content = "\n\n".join(doc.page_content for doc, _ in speech_docs)

        prompt = self.prompt_template.invoke(
            {"context": speech_content, "question": query}
        )

        # Get the answer from the language model
        answer = self.model.invoke(prompt)
        return (answer.content, cos)

    def shutdown(self):
        """Clean up resources if needed."""
        pass
