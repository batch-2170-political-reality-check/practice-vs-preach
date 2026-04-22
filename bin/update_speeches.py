#!/usr/bin/env python
"""
Update ChromaDB with new Bundestag speeches since a given date.

Fetches XML plenary protocols from the Bundestag API, parses them into
individual speech rows, normalizes party names, and appends them to the
existing ChromaDB vector store.

Usage:
    uv run python bin/update_speeches.py --since 2025-11-28
    uv run python bin/update_speeches.py   # auto-detects last embedded date from ChromaDB
"""

import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from requests.exceptions import ChunkedEncodingError, ConnectionError

import json
from practicepreach.tools import process_bundestag_xml, build_tops_lookup
from practicepreach.rag import Rag
from practicepreach.params import BUNDESTAG_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Maps fraktion names from Bundestag XML → canonical party names used in ChromaDB
PARTY_NAME_MAP = {
    'CDU/CSU': 'CDUCSU',
    'AfD': 'AFD',
    'SPD': 'SPD',
    'BÜNDNIS\xa090/DIE GRÜNEN': 'GRÜNEN',   # \xa0 = non-breaking space
    'BÜNDNIS 90/DIE GRÜNEN': 'GRÜNEN',       # regular space fallback
    'Die Linke': 'LINKE',
    'FDP': 'FDP',
    'BSW': 'BSW',
}

BASE_URL = "https://search.dip.bundestag.de/api/v1"
XML_DIR = Path("data/xml_updates")
TOPS_JSON = Path("data/tops.json")


def fetch_session_xml_urls(since_date: str) -> list[tuple[str, str]]:
    """
    Query Bundestag API for plenary sessions since since_date (YYYY-MM-DD).
    Returns list of (datum, xml_url) tuples.
    Paginates backwards through dates until since_date is reached.
    """
    results = []
    end_date = datetime.today().strftime('%Y-%m-%d')
    max_attempts = 3

    while True:
        url = (
            f"{BASE_URL}/plenarprotokoll"
            f"?f.zuordnung=BT"
            f"&f.datum.start={since_date}"
            f"&f.datum.end={end_date}"
            f"&apikey={BUNDESTAG_API_KEY}"
        )

        payload = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                payload = response.json()
                break
            except (ChunkedEncodingError, ConnectionError) as exc:
                logger.warning(f"Attempt {attempt}/{max_attempts} failed: {exc}")
                if attempt < max_attempts:
                    time.sleep(2 * attempt)
            except requests.HTTPError as exc:
                logger.error(f"HTTP {exc.response.status_code}: {exc}")
                break

        if not payload:
            break

        docs = payload.get("documents", [])
        if not docs:
            break

        for doc in docs:
            fundstelle = doc.get("fundstelle", {})
            xml_url = fundstelle.get("xml_url")
            if xml_url:
                results.append((doc.get("datum"), xml_url))

        # Paginate backwards: move end_date to oldest date seen this page
        dates = [doc["datum"] for doc in docs if "datum" in doc]
        new_end = min(dates)
        if new_end >= end_date or new_end < since_date:
            break
        end_date = new_end

    logger.info(f"Found {len(results)} sessions since {since_date}")
    return results


def download_xmls(session_urls: list[tuple[str, str]], xml_dir: Path) -> list[Path]:
    """
    Download XML files to xml_dir. Skips files already downloaded.
    Returns list of local file paths.
    """
    xml_dir.mkdir(parents=True, exist_ok=True)
    local_files = []

    for datum, url in session_urls:
        filename = url.split("/")[-1]
        local_path = xml_dir / filename

        if local_path.exists():
            logger.info(f"Already downloaded: {filename}, skipping")
            local_files.append(local_path)
            continue

        try:
            logger.info(f"Downloading {filename} ({datum})...")
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            local_path.write_bytes(r.content)
            local_files.append(local_path)
        except Exception as exc:
            logger.error(f"Failed to download {url}: {exc}")

    return local_files


def parse_xmls_to_df(xml_files: list[Path]) -> pd.DataFrame:
    """Parse XML files into DataFrame using process_bundestag_xml from tools.py."""
    df = pd.DataFrame(columns=['type', 'date', 'id', 'party', 'top_key', 'text'])

    for xml_file in xml_files:
        logger.info(f"Parsing {xml_file.name}...")
        process_bundestag_xml(str(xml_file), df)

    return df.reset_index(drop=True)


def normalize_parties(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize XML fraktion names to canonical ChromaDB party names."""
    before = set(df['party'].unique())
    df['party'] = df['party'].map(PARTY_NAME_MAP).fillna(df['party'])
    after = set(df['party'].unique())
    unmapped = after - set(PARTY_NAME_MAP.values())
    if unmapped:
        logger.warning(f"Unmapped party names (will be kept as-is): {unmapped}")
    logger.info(f"Party names normalised: {before} → {after}")
    return df


def get_last_embedded_date(rag: Rag) -> str:
    """Read max speech date from ChromaDB and return the next day as YYYY-MM-DD.
    Adding one day avoids re-embedding the last session on every restart."""
    from datetime import timedelta
    meta = rag.vector_store._collection.get(include=["metadatas"])["metadatas"]
    dates = [m["date"] for m in meta if m.get("type") == "speech"]
    if not dates:
        return "2021-10-26"  # fallback: wahlperiode 20 start
    dt = datetime.strptime(str(max(dates)), "%Y%m%d")
    logger.info(f"Last embedded speech date in ChromaDB: {dt.date()}")
    return (dt + timedelta(days=1)).strftime("%Y-%m-%d")


def run_update(rag: Rag, since_date: str = None):
    """
    Run the full update pipeline using an existing Rag instance.
    Can be called from FastAPI lifespan (background thread) or from main().
    """
    since_date = since_date or get_last_embedded_date(rag)
    logger.info(f"Fetching sessions since {since_date}")

    session_urls = fetch_session_xml_urls(since_date)
    if not session_urls:
        logger.info("No new sessions found. Nothing to do.")
        return

    xml_files = download_xmls(session_urls, XML_DIR)

    df = parse_xmls_to_df(xml_files)
    logger.info(f"Parsed {len(df)} speech rows across {len(xml_files)} sessions")

    if df.empty:
        logger.info("No speech rows parsed. Nothing to embed.")
        return

    df = normalize_parties(df)

    staging_csv = f"data/speeches_update_{since_date}.csv"
    df.to_csv(staging_csv, index=False)
    logger.info(f"Saved staging CSV → {staging_csv} ({len(df)} rows)")

    logger.info("Embedding into ChromaDB...")
    n = rag.add_to_vector_store(staging_csv)
    logger.info(f"Done. Embedded {n} new chunks. Total vectors: {rag.get_num_of_vectors()}")


def main():
    parser = argparse.ArgumentParser(description="Update ChromaDB with new Bundestag speeches.")
    parser.add_argument(
        "--since",
        help="Fetch sessions on or after this date (YYYY-MM-DD). Defaults to last embedded date.",
    )
    args = parser.parse_args()

    logger.info("Initialising RAG (loads embedding model)...")
    rag = Rag()
    run_update(rag, since_date=args.since)


if __name__ == "__main__":
    main()
