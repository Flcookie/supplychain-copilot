from __future__ import annotations

import copy
import math
from typing import Protocol

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from core.config import EMBEDDING_MODEL, OPENAI_API_KEY, RERANKER_BACKEND, RERANKER_MODEL


class Reranker(Protocol):
    def rerank(self, query: str, docs: list[Document], top_k: int) -> list[Document]:
        ...


class NoopReranker:
    def rerank(self, query: str, docs: list[Document], top_k: int) -> list[Document]:
        return docs[:top_k]


class CrossEncoderReranker:
    def __init__(self, model_name: str = RERANKER_MODEL):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, docs: list[Document], top_k: int) -> list[Document]:
        pairs = [(query, doc.page_content) for doc in docs]
        scores = self.model.predict(pairs)
        ranked = []
        for doc, score in zip(docs, scores):
            copied = copy.deepcopy(doc)
            copied.metadata["rerank_score"] = float(score)
            ranked.append(copied)
        ranked.sort(key=lambda doc: doc.metadata.get("rerank_score", 0.0), reverse=True)
        return ranked[:top_k]


class OpenAIEmbeddingReranker:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)

    def rerank(self, query: str, docs: list[Document], top_k: int) -> list[Document]:
        if not docs:
            return []
        vectors = self.embeddings.embed_documents([query] + [doc.page_content for doc in docs])
        query_vec = vectors[0]
        doc_vecs = vectors[1:]
        ranked = []
        for doc, vec in zip(docs, doc_vecs):
            copied = copy.deepcopy(doc)
            copied.metadata["rerank_score"] = round(_cosine(query_vec, vec), 4)
            ranked.append(copied)
        ranked.sort(key=lambda doc: doc.metadata.get("rerank_score", 0.0), reverse=True)
        return ranked[:top_k]


def _cosine(a: list[float], b: list[float]) -> float:
    numerator = sum(x * y for x, y in zip(a, b))
    denom = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return numerator / denom if denom else 0.0


def get_reranker() -> Reranker:
    backend = (RERANKER_BACKEND or "none").lower()
    if backend == "cross_encoder":
        return CrossEncoderReranker()
    if backend == "openai":
        return OpenAIEmbeddingReranker()
    return NoopReranker()
