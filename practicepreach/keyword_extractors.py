#%%
from practicepreach.rag import Rag
from datetime import date, datetime
from practicepreach.constants import *
from yake import KeywordExtractor
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

#### Data Imports


#%%
import os
print(os.getcwd())

def import_stopwords():
    PROJECT_ROOT = Path(__file__).resolve().parents[1]  # practice-vs-preach/
    stopwords_path = PROJECT_ROOT / "practicepreach" / "stopwords_de.txt"
    stopwords2_path = PROJECT_ROOT / "practicepreach" / "stopwords_pol.txt"

    # Reading and merging stop words from two different sources
    with stopwords_path.open(encoding="utf-8") as f:
        stop_words1 = [line.strip().lower() for line in f if line.strip()]
    with stopwords2_path.open(encoding="utf-8") as f:
        stop_words2 = [line.strip().lower() for line in f if line.strip()]

    stop_words_clean_all = stop_words1 + stop_words2

    return stop_words_clean_all


stopwords = import_stopwords()

rag = Rag()

#### YAKE Approach

# %%
kw_extractor = KeywordExtractor(
    lan = 'de',
    n = 1,
    #dedupLim = 0.1,
    top = 10,
    #dedupFunc = 'levs',
    stopwords = stopwords,
    )

#%%

def extract_keyword(query,wahlperiode, rag, doctype, stopwords, kw_extractor = None, k = 10):
    keywords_by_party = {party: [] for party in PARTIES_LIST}
    doc_list = []
    party_order = []
    start_date,end_date  = BUNDESTAG_WAHLPERIODE.get(wahlperiode)

    for party in PARTIES_LIST:
        chunks = rag.retrieve_topic_chunks(query,party,start_date,end_date,doctype)
        speech_content = "\n\n".join(doc.page_content for doc, _ in chunks)
        #for debugging
        print(party, "chunks:", len(chunks), "chars:", len(speech_content))

        if kw_extractor is not None:
            try:
                kw_list = kw_extractor.extract_keywords(speech_content) or []
                # normalize to list[(kw, weight)] + cut to top-k
                keywords_by_party[party] = [(kw, float(w)) for kw, w in kw_list][:k]
            except Exception as e:
                # keep empty list, but make the issue visible
                print(f"[kw_extractor error] party={party}: {e}")
                keywords_by_party[party] = []
        else:
            doc_list.append(speech_content)
            party_order.append(party)

    if kw_extractor is not None:
        return keywords_by_party

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words=stopwords,
        ngram_range=(1,1),    # phrases > single words
        max_df=0.85,
        min_df=2,
        sublinear_tf=True
        )

    X = vectorizer.fit_transform(doc_list)
    terms = vectorizer.get_feature_names_out()

    for i, party in enumerate(party_order):
        row = X[i].toarray().ravel()
        idx = row.argsort()[-k:][::-1]
        keywords_by_party[party] = [(terms[j], float(row[j])) for j in idx if row[j] > 0]

    return keywords_by_party

# %%
# climate_20_speech = extract_keyword('Was sagt die Partei über Migration?',20,rag,'speech', kw_extractor = kw_extractor)

# for party, kw_list in climate_20_speech.items():
#     print(f"\n{party}:")
#     for kw, _ in kw_list:
#         print(f"  - {kw}")

keywords = extract_keyword('Was sagt die Partei über Migration?',20,rag,'speech', stopwords)

print(keywords)


# %%
