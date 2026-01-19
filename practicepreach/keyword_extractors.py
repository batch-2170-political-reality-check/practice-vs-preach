#%%
from practicepreach.rag import Rag
from datetime import date, datetime
from practicepreach.constants import BUNDESTAG_WAHLPERIODE
from yake import KeywordExtractor
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

#### Data Imports


#%%
import os
print(os.getcwd())

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # practice-vs-preach/
stopwords_path = PROJECT_ROOT / "data" / "stopwords_de_add.txt"
stopwords2_path = PROJECT_ROOT / "data" / "stopwords.txt"

# Reading and merging stop words from two different sources
with stopwords_path.open(encoding="utf-8") as f:
    stop_words1 = [line.strip().lower() for line in f if line.strip()]
with stopwords2_path.open(encoding="utf-8") as f:
    stop_words2 = [line.strip().lower() for line in f if line.strip()]

stop_words_clean_all = stop_words1 + stop_words2

rag = Rag()

#### YAKE Approach

# %%
kw_extractor = KeywordExtractor(
    lan = 'de',
    n = 1,
    #dedupLim = 0.1,
    top = 10,
    #dedupFunc = 'levs',
    stopwords = stop_words_clean_all,
    )

#%%

def extract_keyword(query,wahlperiode, rag, doctype, kw_extractor = None):
    parties = ['AFD','CDUCSU','LINKE','GRÜNEN','SPD','FDP']
    keywords = {}
    doc_list = []
    start_date = BUNDESTAG_WAHLPERIODE.get(wahlperiode)[0]
    end_date = BUNDESTAG_WAHLPERIODE.get(wahlperiode)[1]

    for party in parties:
        chunks = rag.retrieve_topic_chunks(query,party,start_date,end_date,doctype)
        print(len(chunks))
        speech_content = "\n\n".join(doc.page_content for doc, _ in chunks)
        print(len(speech_content))
        #print(f'Summed length: {len(speech_content)} for {party}')
        if kw_extractor == None:
            doc_list.append(speech_content)
        else:
            top_keywords = kw_extractor.extract_keywords(speech_content)
            keywords[party]=top_keywords

    if len(doc_list)==0:
        return keywords

    else:
            vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words=stop_words_clean_all,
                ngram_range=(1,1),    # phrases > single words
                max_df=0.85,
                min_df=2,
                sublinear_tf=True
                )

            X = vectorizer.fit_transform(doc_list)
            terms = vectorizer.get_feature_names_out()

            def top_terms_for_doc(X, i, k=15):
                row = X[i].toarray().ravel()
                idx = row.argsort()[-k:][::-1]
                return (parties[i], [(terms[j], float(row[j])) for j in idx if row[j] > 0])


            for i in range(len(parties)):
                party, keywords = top_terms_for_doc(X, i=i, k=15)
                print(f"\n{party}")
                print(keywords)

            return X,terms



# %%

climate_20_speech = extract_keyword('Was sagt die Partei über Migration?',20,rag,'speech', kw_extractor = kw_extractor)

for party, kw_list in climate_20_speech.items():
    print(f"\n{party}:")
    for kw, _ in kw_list:
        print(f"  - {kw}")

climate_20_speech = extract_keyword('Was sagt die Partei über Migration?',20,rag,'speech')



# %%
