import logging, http.client as http_client, os

import sys
print(sys.executable)


import pandas as pd

import time

import chromadb
from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_classic import hub
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_core.prompts import ChatPromptTemplate
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import NLTKTextSplitter
from langchain_core.documents import Document

from datetime import datetime

from practicepreach.constants import *
from practicepreach.params import *

GCS_LOCAL_CACHE = "/tmp/chroma_store_e5_3months"
from practicepreach.alignment import analyze_tone_differences
from practicepreach.wahlperiode_converter import *
from practicepreach.cosine_sim import *

#Debug http calls.
# http_client.HTTPConnection.debuglevel = 0
# for name in ("mlflow", "urllib3", "requests"):
#     logging.getLogger(name).setLevel(logging.DEBUG)
#     logging.getLogger(name).addHandler(logging.StreamHandler())

logger = logging.getLogger(__name__)

class Rag:
    def __init__(self):
        # Debugging
        if GOOGLE_API_KEY:
            masked_api_key = '*' * len(GOOGLE_API_KEY)
            logger.info(f"Masked API Key: {masked_api_key}")
        else:
            logger.info("API Key not found in environment variables.")

        device = os.environ.get("TORCH_DEVICE", "cpu")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="intfloat/multilingual-e5-large",
            model_kwargs={"device": device},
            encode_kwargs={"batch_size": 8},
        )
        self.model = init_chat_model("google_genai:gemini-2.5-flash-lite")

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Du bist ein politischer Analyst. Antworte AUSSCHLIESSLICH auf Basis des bereitgestellten Kontexts. Verwende kein Vorwissen.
Falls der Kontext nicht ausreicht, antworte mit: 'Keine ausreichenden Daten für diese Partei und diesen Zeitraum gefunden.'
Jeder Kontextabschnitt beginnt mit der Rede-ID in eckigen Klammern, z.B. [ID216500200].
Formatiere deine Antwort genau so:
**Kernposition:** [ein Satz]

*"[exaktes wörtliches Zitat aus dem Kontext]"* [ID der Rede, aus der das Zitat stammt]
*"[exaktes wörtliches Zitat aus dem Kontext]"* [ID der Rede, aus der das Zitat stammt]
*"[exaktes wörtliches Zitat aus dem Kontext]"* [ID der Rede, aus der das Zitat stammt]

Verwende so viele Zitate wie nötig, um die Kernposition zu belegen. Zitate müssen wortwörtlich aus dem Kontext stammen, jeweils gefolgt von der Rede-ID."""),
            ("human", """Kontext: {context}  Frage: {question}""")
        ])

        # Initialize Chroma - either external, GCS-backed, or embedded
        if USE_EXTERNAL_CHROMA:
            logger.info(f"Connecting to external ChromaDB at {CHROMADB_HOST}:{CHROMADB_PORT}")
            chroma_client = chromadb.HttpClient(
                host=CHROMADB_HOST,
                port=int(CHROMADB_PORT)
            )
            self.vector_store = Chroma(
                client=chroma_client,
                collection_name="political_collection",
                embedding_function=self.embeddings,
            )
        elif USE_GCS_CHROMA:
            logger.info(f"Downloading Chroma store from GCS: {GCS_CHROMA_PATH}")
            self._download_from_gcs(GCS_CHROMA_PATH, GCS_LOCAL_CACHE)
            self.vector_store = Chroma(
                collection_name="political_collection",
                persist_directory=GCS_LOCAL_CACHE,
                embedding_function=self.embeddings,
            )
        else:
            logger.info(f"Using embedded Chroma at {PERSIST_DIR}")
            self.vector_store = Chroma(
                collection_name="political_collection",
                persist_directory=PERSIST_DIR,
                embedding_function=self.embeddings,
            )

            num_of_stored = self.vector_store._collection.count()
            if num_of_stored == 0:
                num_of_chunks_speech = self.add_to_vector_store(DATA_CSV)
                logger.info(f"Embedded {num_of_chunks_speech} chunks into the vector store.")

        num_of_stored = self.vector_store._collection.count()
        logger.info(f"Vector store has {num_of_stored} vectores.")

    def _download_from_gcs(self, gcs_path: str, local_path: str):
        """Download Chroma store from GCS to local cache directory."""
        import subprocess
        import shutil
        if os.path.exists(local_path):
            shutil.rmtree(local_path)
        result = subprocess.run(
            ["gsutil", "-m", "cp", "-r", gcs_path, os.path.dirname(local_path)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"GCS download failed: {result.stderr}")
        logger.info(f"Downloaded Chroma store to {local_path}")

    def upload_to_gcs(self, gcs_path: str = None):
        """Upload local Chroma cache back to GCS after an update."""
        import subprocess
        target = gcs_path or GCS_CHROMA_PATH
        result = subprocess.run(
            ["gsutil", "-m", "cp", "-r", GCS_LOCAL_CACHE, os.path.dirname(target)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"GCS upload failed: {result.stderr}")
        logger.info(f"Uploaded Chroma store to {target}")

    def prune_speeches_before(self, cutoff_date: datetime) -> int:
        """Delete all speech chunks with date < cutoff_date from the vector store.
        Returns the number of chunks deleted.
        """
        cutoff_int = int(cutoff_date.strftime("%Y%m%d"))
        collection = self.vector_store._collection
        result = collection.get(
            where={"$and": [{"type": {"$eq": "speech"}}, {"date": {"$lt": cutoff_int}}]},
            include=[],
        )
        ids = result.get("ids", [])
        if ids:
            collection.delete(ids=ids)
            logger.info(f"Pruned {len(ids)} speech chunks older than {cutoff_date.date()}")
        else:
            logger.info(f"No speech chunks to prune before {cutoff_date.date()}")
        return len(ids)

    def get_num_of_vectors(self) -> int:
        """Get the number of vectors stored in the vector store."""
        return self.vector_store._collection.count()

    def add_to_vector_store(self, data_source):
        """Add new documents to the vector store from CSV file"""
        logger.info(f'Processing file: {data_source}')
        loader = CSVLoader(file_path=data_source, metadata_columns=['date','id','party','type','top_key'])
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


    def embed_and_store(self, doc, text_splitter, batch_size=500):
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

    def _generate_hypothesis(self, query: str) -> str:
        """Generate a hypothetical Bundestag speech passage for HyDE retrieval."""
        response = self.model.invoke(
            f"Schreibe einen kurzen Ausschnitt aus einer Bundestagsrede (3-4 Sätze) auf Deutsch "
            f"zu folgendem Thema: {query}. "
            f"Der Text soll wie ein echter Redeausschnitt klingen."
        )
        logger.debug(f"HyDE hypothesis: {response.content[:100]}")
        return response.content

    def retrieve_topic_chunks(
            self,
            query, party,
            start_date:datetime, end_date:datetime,
            doctype: str,
    ):
        start_date_int = int(start_date.strftime("%Y%m%d"))
        # FIXME start_date=2025-07-21&end_date=2025-12-31 → 500 Internal Server Error
        end_date_int =int(end_date.strftime("%Y%m%d"))

        #ToDo: !!once the csv had a populated type column, add it here to make it queriable
        filter={'$and': [
            {'party': {'$eq': party}},
            {'date': {'$gte':start_date_int}},
            {'date': {'$lte': end_date_int}},
            {'type': {'$eq': doctype}},
        ]}

        hypothesis = self._generate_hypothesis(query)
        retrieved_docs = self.vector_store.similarity_search_with_score(hypothesis, k=50, filter=filter)

        return retrieved_docs


    def answer(self, query, party, start_date:datetime, end_date:datetime, prompt_template=None):
        """Answer a query using the vector store and the language model."""

        logger.debug(f"retrieve_topic_chunks - speech ({party})")
        speech_docs = self.retrieve_topic_chunks(query, party, start_date,
                                                 end_date, doctype='speech')
        speech_docs_len = len(speech_docs)
        logger.debug(f"speech → {speech_docs_len}")

        logger.debug(f"retrieve_topic_chunks - manifesto ({party})")
        manifesto_docs = self.retrieve_topic_chunks(query, party,
                                                    convert_to_wp_start(start_date),
                                                    convert_to_wp_start(end_date),
                                                    doctype='manifesto')
        manifesto_docs_len = len(manifesto_docs)
        logger.debug(f"manifesto → {manifesto_docs_len}")

        # Score
        # Cosine Similarity between speech and query and manifesto and query
        # TODO: Decide if we want to use it in combination with Cosine Similarity between speech and manifesto

        avg_score_speech = sum(score for _, score in speech_docs) / speech_docs_len \
                if speech_docs_len else 0
        avg_score_manifesto = sum(score for _, score in manifesto_docs) / manifesto_docs_len \
                if manifesto_docs_len else 0

        sim_speech = 1- avg_score_speech
        sim_mani = 1 - avg_score_manifesto
        diff = abs(sim_speech - sim_mani)
        align_score = 1 - diff
        # Cosine Similarity between speech and manifesto
        cos = NOT_ENOUGHT_DATA_FOR_SCORE # default
        if speech_docs_len and avg_score_manifesto:
            cos = content_alignment_from_store(self.vector_store,speech_docs,manifesto_docs )
            cos = f"{cos:.2%}"
        cos = f"Alignment score: {cos}"

        if not speech_docs:
            return (None, None)

        # Deduplicate chunks from the same speech to avoid repeated quotes
        seen_ids = set()
        unique_docs = []
        for doc, score in speech_docs:
            doc_id = doc.metadata.get('id')
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_docs.append((doc, score))
        speech_docs = unique_docs

        # Summary
        speech_content = "\n\n".join(
            f"[{doc.metadata.get('id', 'unknown')}] {doc.page_content}"
            for doc, _ in speech_docs
        )

        logger.debug(f"prompt_template.invoke")
        prompt = self.prompt_template.invoke(
            {"context": speech_content, "question": query}
        )

        # Get the answer from the language model
        logger.debug(f"model.invoke")
        answer = self.model.invoke(prompt)
        logger.debug(f"return")
        return (answer.content, cos)

    def summarize_by_top_key(self, top_key: str, party: str) -> str | None:
        """Fetch all speech chunks for a TOP + party and generate a summary."""
        col = self.vector_store._collection
        results = col.get(
            where={"$and": [
                {"type": {"$eq": "speech"}},
                {"top_key": {"$eq": top_key}},
                {"party": {"$eq": party}},
            ]},
            include=["documents", "metadatas"],
        )
        if not results["documents"]:
            return None

        seen_docs = set()
        unique_chunks = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            if doc not in seen_docs:
                seen_docs.add(doc)
                unique_chunks.append((doc, meta))

        context = "\n\n".join(
            f"[{meta.get('id', 'unknown')}] {doc}"
            for doc, meta in unique_chunks
        )

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Du bist ein politischer Analyst. Fasse zusammen, was die Partei zu diesem Tagesordnungspunkt gesagt hat.
Antworte AUSSCHLIESSLICH auf Basis des bereitgestellten Kontexts. Verwende kein Vorwissen.
Formatiere deine Antwort genau so:
**Kernposition:** [ein Satz]

*"[exaktes wörtliches Zitat aus dem Kontext]"* [ID der Rede]
*"[exaktes wörtliches Zitat aus dem Kontext]"* [ID der Rede]"""),
            ("human", "Kontext: {context}"),
        ])
        prompt = prompt_template.invoke({"context": context})
        answer = self.model.invoke(prompt)
        return answer.content

    def shutdown(self):
        """Clean up resources if needed."""
        pass
