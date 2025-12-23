#%%
from practicepreach.rag import Rag
from datetime import date, datetime
from practicepreach.constants import BUNDESTAG_WAHLPERIODE
from yake import KeywordExtractor
from pathlib import Path

#%%
import os
print(os.getcwd())


PROJECT_ROOT = Path(__file__).resolve().parents[1]  # practice-vs-preach/
stopwords_path = PROJECT_ROOT / "data" / "stopwords_de_add.txt"

with stopwords_path.open(encoding="utf-8") as f:
    stopwords = f.read()

# %%
kw_extractor = KeywordExtractor(
    lan = 'de',
    n = 4,
    deduplication_threshold = 0.9,
    numOfKeywords = 10,
    dedup_func = 'levs',
    stopwords = stopwords)


#%%

def string_to_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").date()

#%%

def find_keywords(query,wahlperiode,kw_extractor, rag):
    parties = ['AfD','CDU/CSU','Die Linke','greens','SPD']
    keywords = {}
    start_date = BUNDESTAG_WAHLPERIODE.get(wahlperiode)[0]
    end_date = BUNDESTAG_WAHLPERIODE.get(wahlperiode)[1]

    for party in parties:
        mani_chunks = rag.retrieve_topic_chunks(
                    query,
                    party,
                    start_date=start_date,
                    end_date=end_date,
                    doctype='manifesto')
        mani_join = " ".join(doc.page_content for doc in mani_chunks)
        keyword = kw_extractor.extract_keywords(mani_join)
        # l = [keyword[x][0] for x in range(10)]
        # keywords[party] = l

    return keywords



# %%
rag = Rag()
print(rag.vector_store._collection.count())
print(BUNDESTAG_WAHLPERIODE.get(21)[1])


chunks = rag.retrieve_topic_chunks('What do they say about climate?','AfD',BUNDESTAG_WAHLPERIODE.get(21)[0],BUNDESTAG_WAHLPERIODE.get(21)[1],'manifesto')


filter={'$and': [
            {'party': {'$eq': 'AfD'}},
            # {'date': {'$gte':20241219}},
            # {'date': {'$lte': 20251219}},
            {'type': {'$eq': 'manifesto'}},
        ]}

        # Retrieve similar documents from the vector store

retrieved_docs = rag.vector_store.similarity_search('What do they say about climate?',k=5)
joined = " ".join(doc.page_content for doc in retrieved_docs)


keyword = kw_extractor.extract_keywords(joined)
print(keyword)



print(f'Number of chunks: {len(retrieved_docs)}')


kw = find_keywords('What do they say about climate?',20,kw_extractor,rag)
print(kw)

#find_keywords()
# %%
