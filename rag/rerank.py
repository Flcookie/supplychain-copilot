"""Rerankers for Hybrid RAG funnel: RRF Top-N → Cross-Encoder → Top-K.

Default path uses a local Cross-Encoder (BAAI/bge-reranker-base) so the
retrieval stack is industrial-grade: dual-path recall → RRF fusion → CE rerank.
"""

from __future__ import annotations

import copy
import math
import sys
import time
from typing import Protocol

from langchain_core.documents import Document

from core.config import (
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    RERANKER_BACKEND,
    RERANKER_FALLBACK,
    RERANKER_MODEL,
)


class Reranker(Protocol):
    name: str

    def rerank(self, query: str, docs: list[Document], top_k: int) -> list[Document]:
        ...


class NoopReranker:
    name = "none"

    def rerank(self, query: str, docs: list[Document], top_k: int) -> list[Document]:
        out = []
        for doc in docs[:top_k]:
            copied = copy.deepcopy(doc)
            copied.metadata["rerank_score"] = copied.metadata.get("retrieval_score", 0.0)
            copied.metadata["reranker"] = self.name
            out.append(copied)
        return out


class CrossEncoderReranker:
    """True Cross-Encoder fine-ranker (query, passage) → relevance score.

    Lazy-loads the model on first call so importing rag modules stays cheap.
    """

    name = "cross_encoder"

    def __init__(self, model_name: str = RERANKER_MODEL):
        self.model_name = model_name
        self._model = None

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, docs: list[Document], top_k: int) -> list[Document]:
        if not docs:
            return []
        started = time.perf_counter()
        model = self._ensure_model()
        pairs = [(query, doc.page_content) for doc in docs]
        scores = model.predict(pairs)
        ranked: list[Document] = []
        for doc, score in zip(docs, scores):
            copied = copy.deepcopy(doc)
            copied.metadata["rerank_score"] = float(score)
            copied.metadata["reranker"] = self.name
            copied.metadata["reranker_model"] = self.model_name
            ranked.append(copied)
        ranked.sort(key=lambda doc: doc.metadata.get("rerank_score", 0.0), reverse=True)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        for idx, doc in enumerate(ranked[:top_k], start=1):
            doc.metadata["rerank_rank"] = idx
            doc.metadata["rerank_latency_ms"] = elapsed_ms
        return ranked[:top_k]


class OpenAIEmbeddingReranker:
    """Bi-encoder style fallback: cosine(query_emb, doc_emb). Weaker than CE."""

    name = "openai"

    def __init__(self):
        from langchain_openai import OpenAIEmbeddings

        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)

    def rerank(self, query: str, docs: list[Document], top_k: int) -> list[Document]:
        if not docs:
            return []
        started = time.perf_counter()
        vectors = self.embeddings.embed_documents([query] + [doc.page_content for doc in docs])
        query_vec = vectors[0]
        doc_vecs = vectors[1:]
        ranked: list[Document] = []
        for doc, vec in zip(docs, doc_vecs):
            copied = copy.deepcopy(doc)
            copied.metadata["rerank_score"] = round(_cosine(query_vec, vec), 4)
            copied.metadata["reranker"] = self.name
            ranked.append(copied)
        ranked.sort(key=lambda doc: doc.metadata.get("rerank_score", 0.0), reverse=True)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        for idx, doc in enumerate(ranked[:top_k], start=1):
            doc.metadata["rerank_rank"] = idx
            doc.metadata["rerank_latency_ms"] = elapsed_ms
        return ranked[:top_k]


def _cosine(a: list[float], b: list[float]) -> float:
    numerator = sum(x * y for x, y in zip(a, b))
    denom = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return numerator / denom if denom else 0.0


_RERANKER_SINGLETON: Reranker | None = None
_RERANKER_BACKEND_IN_USE: str | None = None


def _build_cross_encoder() -> Reranker:
    try:
        import sentence_transformers  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Cross-Encoder reranker requires sentence-transformers. "
            "Install with: uv sync --extra rerank"
        ) from exc
    return CrossEncoderReranker(model_name=RERANKER_MODEL)


def _build_backend(name: str) -> Reranker:
    key = (name or "none").lower().strip()
    if key in {"cross_encoder", "ce", "bge"}:
        return _build_cross_encoder()
    if key == "openai":
        return OpenAIEmbeddingReranker()
    if key in {"none", "noop", "off", ""}:
        return NoopReranker()
    raise ValueError(f"Unknown RERANKER_BACKEND={name!r}")


def get_reranker(*, force_reload: bool = False) -> Reranker:
    """Return a process-wide reranker with fallback if Cross-Encoder is unavailable."""
    global _RERANKER_SINGLETON, _RERANKER_BACKEND_IN_USE
    if _RERANKER_SINGLETON is not None and not force_reload:
        return _RERANKER_SINGLETON

    preferred = (RERANKER_BACKEND or "cross_encoder").lower()
    fallback = (RERANKER_FALLBACK or "openai").lower()
    order = [preferred]
    if fallback and fallback not in order:
        order.append(fallback)
    if "none" not in order:
        order.append("none")

    errors: list[str] = []
    for backend in order:
        try:
            reranker = _build_backend(backend)
            _RERANKER_SINGLETON = reranker
            _RERANKER_BACKEND_IN_USE = getattr(reranker, "name", backend)
            if backend != preferred:
                print(
                    f"[rerank] preferred backend={preferred!r} unavailable; "
                    f"using fallback={_RERANKER_BACKEND_IN_USE!r}. "
                    f"Details: {'; '.join(errors) or 'n/a'}",
                    file=sys.stderr,
                )
            return reranker
        except Exception as exc:  # noqa: BLE001 — fall through to next backend
            errors.append(f"{backend}: {exc}")

    _RERANKER_SINGLETON = NoopReranker()
    _RERANKER_BACKEND_IN_USE = "none"
    return _RERANKER_SINGLETON


def active_reranker_name() -> str:
    if _RERANKER_BACKEND_IN_USE:
        return _RERANKER_BACKEND_IN_USE
    return (RERANKER_BACKEND or "cross_encoder").lower()
