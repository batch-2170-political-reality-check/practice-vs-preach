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

from dotenv import load_dotenv

class RAG:
    def __init__(self, vector_store, llm, prompt_template):
        self.vector_store = vector_store
        self.llm = llm
        self.prompt_template = prompt_template

        """Initialize environment variables and any other setup."""
        load_dotenv()  # Load environment variables from .env file

        df = pd.read_csv("data/speeches-wahlperiode-21.csv")

        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        model = init_chat_model("google_genai:gemini-2.5-flash-lite")

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Use the following context to answer the question. Use maximum 7 sentences. Use specific terms. Highlight important ones."),
            ("human", """Context: {context}  Question: {question}""")
        ])

        example_messages = prompt_template.invoke(
            {"context": "(context goes here)", "question": "(question goes here)"}
        ).to_messages()

        vector_store = Chroma(
            collection_name="example_collection",
            embedding_function=embeddings,
        )

        loader = CSVLoader(file_path="data/speeches-wahlperiode-21.csv",
                   metadata_columns=['date','id','party'])
        data = loader.load()

        text_splitter = NLTKTextSplitter(
            chunk_size=500,
            chunk_overlap=200
        )

    def embed_and_store_pdf(self, file_path, vector_store, batch_size=200):
        """Load a PDF file, split it into chunks, and store the chunks in a vector store."""
        # Load the PDF file
        loader = PyPDFLoader(file_path, mode="single")
        pdf = loader.load()

        # Split the pages into chunks
        all_splits = text_splitter.split_documents(pdf)

        # Add the party name to the metadata
        pattern = r"(?<=data/)[^_]+(?=_)"
        party_name = re.search(pattern, file_path)

        for split in all_splits:
            split.metadata["party_name"] = party_name.group()

        # Add the chunks to the vector store in batches
        for i in range(0, len(all_splits), batch_size):
            batch = all_splits[i:i + batch_size]
            vector_store.add_documents(documents=batch)

        return f"{file_path} embedded"

    def answer(self, query, vector_store, llm, file, prompt_template=None):
        """Answer a query using the vector store and the language model."""
        # Retrieve similar documents from the vector store
        retrieved_docs = vector_store.similarity_search(query,k=50, filter={'source': file})

        # Create the prompt
        docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)

        # If no prompt template is provided, use the default one
        if not prompt_template:
            prompt_template = hub.pull("rlm/rag-prompt")

        prompt = prompt_template.invoke(
            {"context": docs_content, "question": query}
     )

        # Get the answer from the language model
        answer = llm.invoke(prompt)
        return answer.content

    def shutdown(self):
        """Clean up resources if needed."""
        pass
