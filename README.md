# Practice vs Preach: Political Alignment Analysis System

A RAG-based system that compares German political parties' parliamentary speeches with their election manifestos to measure alignment and identify gaps between what parties promise and what they actually argue for in parliament.

## Overview

This system answers: *"What does each party actually say in parliament, and how well does it align with what they promised in their manifesto?"*

### Key Features

- **Dual Data Sources**: Parliamentary speeches (Bundestag API) and election manifestos (Manifesto Project API)
- **Semantic Search**: Vector-based retrieval using `multilingual-e5-large` embeddings (HuggingFace, runs locally)
- **Alignment Scoring**: Cosine similarity between speech and manifesto embeddings
- **Topic-Based Analysis**: 10 political topics across configurable date ranges and election periods (Wahlperioden)
- **Auto-Updating**: On startup, the API automatically fetches and embeds the latest Bundestag sessions
- **RESTful API**: FastAPI service for querying summaries and alignment scores

- **Next Up: CMP Code Mapping**: Keywords extracted from speeches are matched to Comparative Manifesto Project codes

## Architecture

```
┌─────────────────────┐        ┌──────────────────────────┐
│   Bundestag API     │        │   Manifesto Project API  │
│  (XML Protocols)    │        │   (JSON + TXT files)     │
└────────┬────────────┘        └────────────┬─────────────┘
         │                                  │
         ▼                                  ▼
┌────────────────────────────────────────────────────────┐
│                 Data Processing Pipeline               │
│  bin/update_speeches.py  │  bin/download_manifestos.py │
│  - XML parsing           │  - Manifesto API fetch       │
│  - Party normalisation   │  - Sentence-aware chunking   │
│  - CSV export            │  - CSV export                │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│              Vector Store (ChromaDB)                   │
│  - multilingual-e5-large embeddings (1024 dims)        │
│  - Metadata: party, date (YYYYMMDD int), type, id      │
│  - Filtered retrieval by party + date range + type     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               RAG Query System (rag.py)                │
│  - Dual retrieval: speech chunks + manifesto chunks    │
│  - Cosine similarity alignment scoring                 │
│  - Gemini 2.5 Flash Lite summary generation            │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                FastAPI Service (fast.py)               │
│  GET /summaries   GET /parameters   GET /             │
└────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Python 3.12+**, managed with [uv](https://docs.astral.sh/uv/)
- **LangChain**: Document loading, text splitting, LLM orchestration, ChromaDB integration
- **ChromaDB**: Persistent vector database (embedded local or external HTTP mode)
- **HuggingFace** `intfloat/multilingual-e5-large`: Multilingual sentence embeddings (runs locally, MPS on Apple Silicon)
- **Google Gemini** `gemini-2.5-flash-lite`: LLM for summary generation
- **FastAPI**: REST API framework with async parallel party processing
- **NLTK**: Sentence-boundary-aware text splitting
- **Pandas**: Data processing pipeline
- **Docker + Terraform**: GCP Cloud Run deployment

## Project Structure

```
practice-vs-preach/
├── practicepreach/                      # Main application package
│   ├── rag.py                          # Core RAG: vector store, retrieval, LLM answers
│   ├── fast.py                         # FastAPI app + background speech updater
│   ├── tools.py                        # Bundestag XML parser + Chroma vectorizer CLI
│   ├── alignment.py                    # LLM-based tone & alignment analysis
│   ├── constants.py                    # Wahlperiode dates, party codes, topics
│   ├── cosine_sim.py                   # Cosine similarity between speech/manifesto chunks
│   ├── keyword_extractors.py           # TF-IDF keyword extraction per party
│   ├── keyword_cmp_matching.py         # Map keywords → CMP annotation codes
│   ├── cmp_visualisation.py            # Bar chart: dominant CMP codes per keyword
│   ├── manifesto_model.py              # ManifestoBERTa: policy topic classification
│   ├── generate_manifesto_dataframe.py # Manifesto text files → chunked CSV
│   ├── wahlperiode_converter.py        # Date → Wahlperiode period converter
│   └── params.py                       # Environment variable configuration
├── bin/
│   ├── update_speeches.py              # Fetch + parse + embed new Bundestag sessions
│   ├── download_manifestos.py          # Download manifestos from Manifesto Project API
│   ├── entrypoint.sh                   # Docker entrypoint (starts uvicorn)
│   ├── add_vectors.sh                  # Shell wrapper: vectorize a CSV into ChromaDB
│   └── get_speeches.sh                 # Shell wrapper: fetch speeches
├── data/
│   ├── chroma_store_e5/                # ChromaDB vector store (multilingual-e5-large)
│   ├── german_manifestos/              # Raw manifesto JSON + TXT files
│   ├── data_manifestos-plus-*.csv      # Combined speech + manifesto data (main input)
│   └── xml_updates/                    # Downloaded XML plenary protocols (cached)
├── notebooks/                          # Exploration notebooks
├── terraform/                          # GCP Cloud Run infrastructure
├── Dockerfile
├── Makefile
└── pyproject.toml
```

## Setup

### Prerequisites

- Python 3.12+
- `uv` package manager
- Google Cloud account (for Gemini API)

### Installation

```bash
git clone <repository-url>
cd practice-vs-preach
uv sync
```

Download NLTK punkt tokenizer (required for text splitting):

```python
import nltk
nltk.download('punkt_tab')
```

### Configuration

Copy `.env.sample` to `.env` and fill in:

```bash
# Google AI (required for LLM summaries)
GOOGLE_API_KEY=your_google_api_key

# Bundestag API (public key — used for fetching speeches)
BUNDESTAG_API_KEY=your_bundestag_api_key

# Manifesto Project API
MANIFESTO_API_KEY=your_manifesto_api_key
MANIFESTO_START_DATE=2021-01-01

# Vector store path (local embedded mode)
PERSIST_DIR=data/chroma_store_e5

# Path to combined speech + manifesto CSV (used to populate store if empty)
DATA_CSV=data/data_manifestos-plus-20-and-21-wahlperiode.csv

# Optional: external ChromaDB (deployed mode)
# CHROMADB_HOST=your_chromadb_host
# CHROMADB_PORT=8000
```

## Data Pipeline

### 1. Download Manifestos

```bash
uv run python bin/download_manifestos.py
```

Fetches party manifestos from the Manifesto Project API and saves them to `data/german_manifestos/`. Then generate the chunked CSV:

```bash
uv run python -m practicepreach.generate_manifesto_dataframe
```

### 2. Fetch Parliamentary Speeches

```bash
uv run python bin/update_speeches.py --since 2021-10-26
```

Fetches XML plenary protocols from the Bundestag API, parses individual speeches by party, normalizes party names, and embeds them into ChromaDB. Running without `--since` auto-detects the last embedded date.

### 3. Build the Combined CSV (one-time)

```python
import pandas as pd
manifestos = pd.read_csv('data/manifestos.csv')
speeches = pd.read_csv('data/speeches.csv')
pd.concat([manifestos, speeches]).to_csv('data/data_manifestos-plus-20-and-21-wahlperiode.csv', index=False)
```

### 4. Vectorize (if starting from scratch)

```bash
uv run python -m practicepreach.tools vectorize data/data_manifestos-plus-20-and-21-wahlperiode.csv
```

## Running the API

```bash
# Development
uv run uvicorn practicepreach.fast:app --reload

# Production (Docker)
make docker-build
make docker-run
```

On startup, the API automatically fetches and embeds any Bundestag sessions published since the last update, in a background thread.

## API Endpoints

### `GET /`
Health check.

### `GET /parameters`
Returns available political topics and Wahlperiode date ranges.

```json
{
  "political_topics": {
    "economy": "Economy & Growth / Germany as an Industrial Nation",
    "environment": "Climate, Environment & Energy"
  },
  "bundestag_wahlperiode": {
    "20": ["2021-10-26", "2025-03-22"],
    "21": ["2025-03-23", "..."]
  }
}
```

### `GET /summaries`

Returns topic summaries and alignment scores for all parties, processed in parallel.

**Parameters:**
- `topic` — topic key from `/parameters` (e.g. `"environment"`)
- `start_date` — `YYYY-MM-DD`
- `end_date` — `YYYY-MM-DD`

**Example:**
```bash
GET /summaries?topic=migration&start_date=2023-01-01&end_date=2025-03-22
```

**Response:**
```json
{
  "SPD": {
    "summary": "Die SPD betont in ihren Reden...",
    "label": "Alignment score: 72.4%"
  },
  "AFD": {
    "summary": "Die AfD fordert...",
    "label": "Alignment score: 81.2%"
  }
}
```

The alignment score is a cosine similarity between the centroid of the retrieved speech chunks and the centroid of the corresponding manifesto chunks.

## Deployment

### Docker + Cloud Run

```bash
make deploy-dev    # Build, push, deploy to Cloud Run (dev)
make deploy        # Direct Cloud Run deployment (2 CPUs, 8GB memory)
```

### Terraform

Infrastructure is defined in `terraform/` for Cloud Run, IAM, and storage.

```bash
make deploy-terraform
```

### Deployment Modes

The system supports two ChromaDB modes controlled by environment variables:

| Mode | Config | Use case |
|------|--------|----------|
| **Embedded** | `PERSIST_DIR=...` | Local development, single instance |
| **External** | `CHROMADB_HOST=...` | Production, concurrent access |

## Political Topics

| Key | Topic |
|-----|-------|
| `economy` | Economy & Growth / Germany as an Industrial Nation |
| `social` | Social Security & Welfare / Pensions |
| `work` | Work, Labour Market & Skilled Workers |
| `education` | Education & Equal Opportunities |
| `environment` | Climate, Environment & Energy |
| `migration` | Migration, Integration & Citizenship |
| `housing` | Housing & Urban Development |
| `technology` | Digitalization & Technological Innovation |
| `security` | Internal Security, Law & Order |
| `foreign_policy` | Foreign Policy, Security & Europe |

## Supported Parties

`AFD`, `SPD`, `CDUCSU`, `GRÜNEN`, `LINKE`

## Limitations & Roadmap

**Current (Phase 1)**:
- Speech-based topic summaries with alignment score vs manifesto
- CMP code keyword matching and visualisation
- Auto-updating ChromaDB from Bundestag API

**Planned (Phase 2)**:
- Separate speech summary and manifesto summary in `/summaries` response
- Subtopic extraction via clustering
- Tonality classification (supportive, critical, conditional)

**Future (Phase 3)**:
- Quote extraction with links to source speeches
- Speaker attribution

## Acknowledgments

- [Bundestag Open Data API](https://dip.bundestag.de/)
- [Manifesto Project](https://manifesto-project.wzb.eu/)
- [LangChain](https://python.langchain.com/)
- [intfloat/multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large)
