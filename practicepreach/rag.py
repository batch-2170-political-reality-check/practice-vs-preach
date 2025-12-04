import pandas as pd
import os
from pprint import pprint
from IPython.display import Markdown
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
import pprint
from langchain_core.prompts import ChatPromptTemplate
import re
from langchain_chroma import Chroma
from langchain.chat_models import init_chat_model
from langchain_classic import hub
import json
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_text_splitters import NLTKTextSplitter

from practicepreach.params import *

class Rag:
    def __init__(self):

        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        self.model = init_chat_model("google_genai:gemini-2.5-flash-lite")

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Use the following context to answer the question. Use maximum 7 sentences. Use specific terms. Highlight important ones."),
            ("human", """Context: {context}  Question: {question}""")
        ])

        self.example_messages = self.prompt_template.invoke(
            {"context": "(context goes here)", "question": "(question goes here)"}
        ).to_messages()

        self.vector_store = Chroma(
            collection_name="political_collection",
            persist_directory=PERSIST_DIR,
            embedding_function=self.embeddings,
        )

        num_of_stored = self.vector_store._collection.count()

        if num_of_stored == 0:
            loader = CSVLoader(file_path=SPEECHES_CSV, metadata_columns=['date','id','party'])
            data = loader.load()
            text_splitter = NLTKTextSplitter(
                chunk_size=500,
                chunk_overlap=200
            )
            num_of_chunks = self.embed_and_store(data, text_splitter)
            print(f"Embedded {num_of_chunks} chunks into the vector store.")
        else:
            print(f"Vector store already has {num_of_stored} vectores. Skipping embedding.")

    def embed_and_store(self, doc, text_splitter, batch_size=200):
        """Split JSON-loaded documents into chunks and store them in a vector store."""
        # Split the pages into chunks
        all_splits = text_splitter.split_documents(doc)

        # Add the chunks to the vector store in batches
        for i in range(0, len(all_splits), batch_size):
            batch = all_splits[i:i + batch_size]
            self.vector_store.add_documents(documents=batch)

        return f"{len(all_splits)} chunks embedded"

    def answer(self, query, party, date, prompt_template=None):
        """Answer a query using the vector store and the language model."""

        filter={'$and': [{'party': {'$eq': party}}, {'date': {'$eq': date}}]}

        # Retrieve similar documents from the vector store
        retrieved_docs = self.vector_store.similarity_search(query,k=50, filter=filter)

        # Create the prompt
        docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)

        # If no prompt template is provided, use the default one
        if not self.prompt_template:
            self.prompt_template = hub.pull("rlm/rag-prompt")

        prompt = self.prompt_template.invoke(
            {"context": docs_content, "question": query}
        )

        # Get the answer from the language model
        answer = self.llm.invoke(prompt)
        return answer.content

    def shutdown(self):
        """Clean up resources if needed."""
        pass
