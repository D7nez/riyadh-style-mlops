import csv, hashlib, json
from pathlib import Path
import numpy as np
from langsmith import traceable
from sklearn.feature_extraction.text import TfidfVectorizer

def boolean(value):
    return str(value).strip().lower() in {"true", "1", "1.0", "yes"}
class Retriever:
    def __init__(self, settings):
        self.settings = settings
        raw = Path(settings.data).read_bytes()
        self.data_hash = hashlib.sha256(raw).hexdigest()
        with open(settings.data, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows or "clean_text" not in rows[0]: raise ValueError("CSV requires clean_text")
        self.rows = [r for r in rows if r["clean_text"].strip()]
        if not self.rows: raise ValueError("CSV has no non-empty texts")
        for row in self.rows:
            for flag in ["has_stats", "has_religious"]: row[flag] = boolean(row.get(flag, ""))
        texts = [(r.get("title_clean", "") + " " + r["clean_text"][:400]) for r in self.rows]
        if settings.retrieval == "e5":
            from sentence_transformers import SentenceTransformer
            self.encoder = SentenceTransformer(settings.embedding_model)
            cache = Path(settings.cache);cache.mkdir(parents=True, exist_ok=True)
            key = hashlib.sha256((self.data_hash + settings.embedding_model + "passage-v1").encode()).hexdigest()
            file = cache / (key + ".npy")
            if file.exists(): self.matrix = np.load(file, allow_pickle=False)
            else:
                self.matrix = self.encoder.encode(["passage: " + t for t in texts], normalize_embeddings=True)
                np.save(file,self.matrix,allow_pickle=False)
        else:
            self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5))
            self.matrix = self.vectorizer.fit_transform(texts)
    @traceable(name="retrieve_examples", run_type="retriever")
    def retrieve(self, text, meta, exclude_ids=None):
        if self.settings.retrieval == "e5":
            q = self.encoder.encode(["query: " + text], normalize_embeddings=True)
            similarities = (self.matrix @ q.T).ravel()
        else:
            similarities = (self.matrix @ self.vectorizer.transform([text]).T).toarray().ravel()
        scored=[]
        for i,row in enumerate(self.rows):
            if row.get("id") in (exclude_ids or set()): continue
            sim=float(similarities[i]);score=sim
            if meta.topic and row.get("topic")==meta.topic: score+=0.15
            if meta.has_stats and row["has_stats"]: score+=0.05
            if meta.has_religious and row["has_religious"]: score+=0.05
            scored.append({"id":row.get("id",str(i)),"title":row.get("title_clean",""),"text":row["clean_text"],"topic":row.get("topic",""),"similarity":sim,"score":score})
        return sorted(scored,key=lambda x:(-x["score"],x["id"]))[:self.settings.top_k]
