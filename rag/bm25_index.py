import os
import pickle
import re
from dataclasses import dataclass

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi


BM25_INDEX_PATH = os.path.join("data", "bm25_index.pkl")


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]", text.lower())


@dataclass
class BM25SearchResult:
    doc: Document
    score: float


class LocalBM25Index:
    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.corpus = [tokenize(doc.page_content) for doc in docs]
        self.bm25 = BM25Okapi(self.corpus) if self.corpus else None

    def search(self, query: str, k: int = 20, doc_types: list[str] | None = None) -> list[BM25SearchResult]:
        if not self.bm25 or not self.docs:
            return []
        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        candidates = []
        allowed = set(doc_types or [])
        for doc, score in zip(self.docs, scores):
            if allowed and doc.metadata.get("doc_type") not in allowed:
                continue
            candidates.append(BM25SearchResult(doc=doc, score=float(score)))
        return sorted(candidates, key=lambda item: item.score, reverse=True)[:k]


def save_bm25_index(docs: list[Document], path: str = BM25_INDEX_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(LocalBM25Index(docs), f)


def load_bm25_index(path: str = BM25_INDEX_PATH) -> LocalBM25Index | None:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)
