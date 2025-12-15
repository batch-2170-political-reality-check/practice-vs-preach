# Practice vs Preach: Political Alignment Analysis System

A RAG-based system that compares German political parties' parliamentary speeches with their election manifestos to measure alignment and identify gaps between promises and actions.

## Overview

This system answers: "What does each party actually talk about in parliament, and how well does it align with what they promised in their manifesto?"

### Key Features

- **Dual Data Sources**: Processes both parliamentary speeches (from Bundestag API) and election manifestos
- **Semantic Search**: Vector-based retrieval using Google Generative AI embeddings
- **Alignment Scoring**: Combines cosine similarity
- **Topic-Based Analysis**: Analyzes alignment across 10 political topics
- **RESTful API**: FastAPI service for querying summaries and alignment scores

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│ Bundestag API   │     │ Manifesto Files │
│  (Speeches)     │     │   (.txt, .json) │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
    ┌─────────────────────────────────┐
    │   Data Processing Pipeline      │
    │  - CSV Conversion                │
    │  - Sentence-Aware Chunking       │
    │  - Metadata Extraction           │
    └──────────────┬──────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────┐
    │      Vector Store (ChromaDB)    │
    │  - Google Embeddings            │
    │  - Metadata Filtering           │
    └──────────────┬──────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────┐
    │      RAG Query System           │
    │  - Dual Retrieval (Speech/Manifesto)│
    │  - Alignment Scoring             │
    │  - Summary Generation           │
    └──────────────┬──────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────┐
    │      FastAPI Service            │
    │  - /summaries endpoint          │
    │  - /parameters endpoint         │
    └─────────────────────────────────┘
```

## Tech Stack

- **Python 3.12+**
- **LangChain**: Document processing, LLM orchestration, vector store integration
- **ChromaDB**: Persistent vector database
- **Google Generative AI**: 
  - `text-embedding-004` for embeddings
  - `gemini-2.5-flash-lite` for text analysis
- **FastAPI**: REST API framework
- **NLTK**: Sentence tokenization
- **Pandas**: Data processing
- **Terraform**: Infrastructure as code (GCP Cloud Run)

## Project Structure

```
practice-vs-preach/
├── practicepreach/          # Main application package
│   ├── rag.py              # RAG system core
│   ├── alignment.py        # LLM-based alignment analysis
│   ├── fast.py             # FastAPI application
│   ├── tools.py            # Bundestag API integration
│   ├── generate_manifesto_dataframe.py  # Manifesto processing
│   ├── constants.py        # Political topics, wahlperiode dates
│   ├── cosine_sim.py       # Similarity calculations
│   └── params.py           # Configuration management
├── data/                    # Data storage
│   ├── speeches-wahlperiode-*.csv  # Parliamentary speeches
│   └── manifestos.csv      # Processed manifestos
├── notebooks/               # Jupyter notebooks for exploration
├── terraform/               # Infrastructure configuration
└── requirements.txt         # Python dependencies
```

## Installation

### Prerequisites

- Python 3.12+
- Google Cloud account with Generative AI API access
- Environment variables configured (see Configuration)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd practice-vs-preach
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (see Configuration section)

4. Download NLTK data:
```python
import nltk
nltk.download('punkt')
```

## Configuration

Set the following environment variables:

```bash
# Google AI API
GOOGLE_API_KEY=your_google_api_key

# Data paths
SPEECHES_CSV=data/speeches-wahlperiode-21.csv
PERSIST_DIR=data/chroma_store

# Optional
SPEECHES_XML_DIR=data/xml  # For storing raw XML files
```

## Usage

### Running the API Server

```bash
# Development
uvicorn practicepreach.fast:app --reload

# Production (via Docker)
make docker-deploy
```

### API Endpoints

#### `GET /`
Health check endpoint.

#### `GET /parameters`
Returns available political topics and wahlperiode date ranges.

**Response:**
```json
{
  "political_topics": {
    "economy": "Economy & Growth / Germany as an Industrial Nation",
    "environment": "Climate, Environment & Energy",
    ...
  },
  "bundestag_wahlperiode": {
    "20": ["2021-10-26", "2025-03-22"],
    ...
  }
}
```

#### `GET /summaries`
Query summaries and alignment scores for all parties.

**Parameters:**
- `topic` (str): Political topic key (e.g., "economy", "environment")
- `start_date` (str): Start date in `YYYY-MM-DD` format
- `end_date` (str): End date in `YYYY-MM-DD` format

**Example:**
```bash
GET /summaries?topic=environment&start_date=2021-10-26&end_date=2023-12-31
```

**Response:**
```json
{
  "AfD": {
    "summary": "Party's stance on climate policy...",
    "label": "Aligns mostly with manifesto"
  },
  "SPD": {
    "summary": "...",
    "label": "Aligns well with manifesto"
  },
  ...
}
```

### Programmatic Usage

```python
from practicepreach.rag import Rag
from datetime import datetime

# Initialize RAG system
rag = Rag(populate_vector_store=True)

# Query for a specific party and topic
query = "What does the party say about Climate, Environment & Energy"
party = "SPD"
start_date = datetime(2021, 10, 26)
end_date = datetime(2023, 12, 31)

summary, alignment_score = rag.answer(query, party, start_date, end_date)
```

## Data Processing

### Processing Manifestos

```python
from practicepreach.generate_manifesto_dataframe import generate_manifesto_dataframe

# Generate and save manifesto CSV
df = generate_manifesto_dataframe()
# CSV automatically saved to data/manifestos.csv
```

The script:
- Reads `.txt` files from `german_manifestos/` folder
- Extracts party ID from filename (e.g., `41113_202109_text.txt` → party ID `41113`)
- Maps party ID to party name via `parties_summary.csv`
- Extracts year and maps to wahlperiode start date
- Chunks text by sentences (never cutting sentences)
- Outputs CSV with columns: `type`, `date`, `id`, `party`, `text`

### Fetching Parliamentary Speeches

```python
from practicepreach.tools import get_speeches

# Fetch speeches from Bundestag API
get_speeches()
# Saves to CSV specified in SPEECHES_CSV environment variable
```

## How It Works

### 1. Data Ingestion
- **Speeches**: Fetched from Bundestag API, processed into CSV with metadata
- **Manifestos**: Processed from text files, chunked by sentences, stored in CSV

### 2. Vector Store Population
- Documents are loaded via `CSVLoader` with metadata columns
- Text is chunked using `NLTKTextSplitter` (500 chars, 200 overlap)
- Chunks are embedded using Google's `text-embedding-004`
- Embeddings stored in ChromaDB with metadata (party, date, type, id)

### 3. Query Processing
- User provides: topic, date range
- System retrieves relevant chunks from both:
  - **Speeches**: Filtered by party, date range, type='speech'
  - **Manifestos**: Filtered by party, wahlperiode dates, type='manifesto'
- Uses `similarity_search_with_score` for semantic retrieval

### 4. Alignment Analysis
- **Cosine Similarity**: Computes similarity between speech and manifesto chunks

### 5. Summary Generation
- Retrieved speech chunks are passed to Gemini with the topic query
- LLM generates concise summary (max 7 sentences)
- Returns summary + alignment label for each party


## Political Topics

The system analyzes 10 political topics:
- Economy & Growth
- Social Security & Welfare
- Work, Labour Market & Skilled Workers
- Education & Equal Opportunities
- Climate, Environment & Energy
- Migration, Integration & Citizenship
- Housing & Urban Development
- Digitalization & Technological Innovation
- Internal Security, Law & Order
- Foreign Policy, Security & Europe

## Development

### Running Tests

```bash
pytest
```

### Code Structure

- **`rag.py`**: Core RAG system, vector store management, query processing
- **`alignment.py`**: LLM-based tone and alignment analysis
- **`fast.py`**: FastAPI application and endpoints
- **`tools.py`**: Bundestag API integration, speech extraction
- **`generate_manifesto_dataframe.py`**: Manifesto processing pipeline
- **`constants.py`**: Domain constants (topics, wahlperiode dates, parties)

## Deployment

### Docker

```bash
# Build and deploy to Cloud Run
make docker-deploy
```

### Terraform

Infrastructure is managed via Terraform in the `terraform/` directory:
- Cloud Run service configuration
- IAM roles and permissions
- Storage buckets

## Limitations & Future Work

**Current (Phase 1)**:
- Topic-level summaries
- Basic alignment scoring

**Planned (Phase 2)**:
- Subtopic extraction via clustering
- Tonality classification (supportive, critical, conditional)

**Future (Phase 3)**:
- Quote extraction with context
- Speaker attribution and links to full speeches

## Acknowledgments

- Bundestag Open Data API
- Manifesto Project for German political manifestos
- LangChain community
- Google Generative AI

## Contact

[Add contact information]
