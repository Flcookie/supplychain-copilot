"""Hybrid RAG: dual-path recall (vector + BM25) → RRF fusion → Cross-Encoder rerank.

Funnel (industrial default):
  vector_k / keyword_k (~30)  →  RRF merge  →  Top `rerank_pool` (20)
  → Cross-Encoder fine-rank  →  Top `k` (5) to the generator.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from langchain_core.documents import Document

from core.config import ENABLE_HYDE, RERANK_POOL
from core.resilience import BM25_ONLY_LIMITATION_EN, record_resilience_event
from rag.bm25_index import load_bm25_index, tokenize
from rag.query_expansion import build_hyde_query, build_keyword_query


# Reciprocal Rank Fusion constant. Lower => earlier ranks dominate more.
RRF_K = 60


class HybridRetriever:
    def __init__(
        self,
        *,
        k: int = 5,
        vector_k: int = 30,
        keyword_k: int = 30,
        rerank_pool: int | None = None,
        doc_types: list[str] | None = None,
        reranker: Any | None = None,
        bm25: Any | None = None,
        vectorstore: Any | None = None,
    ):
        self.k = k
        self.vector_k = vector_k
        self.keyword_k = keyword_k
        self.rerank_pool = rerank_pool if rerank_pool is not None else RERANK_POOL
        self.doc_types = doc_types
        self.reranker = reranker
        self._vectorstore = vectorstore
        self._vector_failed = False
        self.bm25 = bm25 if bm25 is not None else load_bm25_index()
        self.last_degraded = False
        self.last_degrade_reason: str | None = None

    def _mark_degraded(self, reason: str) -> None:
        if self.last_degraded:
            return
        self.last_degraded = True
        self.last_degrade_reason = reason
        record_resilience_event(
            "partial_degradation",
            from_backend="pinecone",
            to_backend="bm25_only",
            reason=reason,
        )

    def _get_vectorstore(self) -> Any | None:
        if self._vector_failed:
            return None
        if self._vectorstore is not None:
            return self._vectorstore
        try:
            from rag.retriever import get_vectorstore

            self._vectorstore = get_vectorstore()
            return self._vectorstore
        except Exception as exc:  # noqa: BLE001 — degrade instead of failing the turn
            self._vector_failed = True
            self._mark_degraded(f"pinecone_init: {exc}")
            return None

    def invoke(self, query: str) -> list[Document]:
        candidates: dict[str, dict[str, Any]] = {}
        self.last_degraded = False
        self.last_degrade_reason = None

        vectorstore = self._get_vectorstore()
        if vectorstore is not None:
            try:
                for route, vector_query, route_k in self._vector_queries(query):
                    results = self._vector_search(vector_query, route_k)
                    for rank, (doc, score) in enumerate(results, start=1):
                        key = self._doc_key(doc)
                        item = candidates.setdefault(
                            key,
                            {
                                "doc": doc,
                                "vector_score": 0.0,
                                "keyword_score": 0.0,
                                "rrf_score": 0.0,
                                "routes": [],
                            },
                        )
                        item["vector_score"] = max(
                            item["vector_score"], self._normalize_vector_score(score)
                        )
                        item["rrf_score"] += 1.0 / (RRF_K + rank)
                        item["routes"].append(route)
            except Exception as exc:  # noqa: BLE001
                self._vector_failed = True
                self._mark_degraded(f"pinecone_search: {exc}")
                candidates = {}
        elif not self.last_degraded:
            self._mark_degraded("vectorstore_unavailable")

        if self.bm25:
            keyword_query = build_keyword_query(query)
            keyword_results = self.bm25.search(keyword_query, k=self.keyword_k, doc_types=self.doc_types)
            max_keyword = max([item.score for item in keyword_results], default=1.0) or 1.0
            for rank, result in enumerate(keyword_results, start=1):
                key = self._doc_key(result.doc)
                item = candidates.setdefault(
                    key,
                    {
                        "doc": result.doc,
                        "vector_score": 0.0,
                        "keyword_score": 0.0,
                        "rrf_score": 0.0,
                        "routes": [],
                    },
                )
                item["keyword_score"] = max(item["keyword_score"], result.score / max_keyword)
                item["rrf_score"] += 1.0 / (RRF_K + rank)
                item["routes"].append("keyword")

        fused_docs = []
        for item in candidates.values():
            doc = copy.deepcopy(item["doc"])
            metadata_boost = self._metadata_boost(doc, query)
            fused_score = item["rrf_score"] + 0.05 * metadata_boost
            doc.metadata["vector_score"] = round(item["vector_score"], 4)
            doc.metadata["keyword_score"] = round(item["keyword_score"], 4)
            doc.metadata["metadata_boost"] = round(metadata_boost, 4)
            doc.metadata["rrf_score"] = round(item["rrf_score"], 4)
            doc.metadata["retrieval_score"] = round(fused_score, 4)
            doc.metadata["retrieval_routes"] = sorted(set(item["routes"]))
            fused_docs.append(doc)

        fused_docs.sort(key=lambda doc: doc.metadata.get("retrieval_score", 0.0), reverse=True)
        pool_size = max(self.rerank_pool, self.k)
        rerank_input = fused_docs[:pool_size]

        # Annotate pre-rerank ranks for observability / interview traces.
        for idx, doc in enumerate(rerank_input, start=1):
            doc.metadata["rrf_rank"] = idx
            doc.metadata["rerank_pool_size"] = pool_size
            if self.last_degraded:
                doc.metadata["retrieval_degraded"] = True
                doc.metadata["retrieval_mode"] = "bm25_only"
                doc.metadata["retrieval_limitation"] = BM25_ONLY_LIMITATION_EN

        if self.reranker:
            reranked = self.reranker.rerank(query, rerank_input, top_k=self.k)
            for doc in reranked:
                funnel = (
                    f"bm25_only→top{self.k}"
                    if self.last_degraded
                    else (
                        f"dual_recall→RRF_top{pool_size}→"
                        f"{getattr(self.reranker, 'name', 'rerank')}_top{self.k}"
                    )
                )
                doc.metadata["retrieval_funnel"] = funnel
                if self.last_degraded:
                    doc.metadata["retrieval_degraded"] = True
                    doc.metadata["retrieval_mode"] = "bm25_only"
                    doc.metadata["retrieval_limitation"] = BM25_ONLY_LIMITATION_EN
            return reranked

        out = rerank_input[: self.k]
        for doc in out:
            doc.metadata["retrieval_funnel"] = (
                f"bm25_only→top{self.k}" if self.last_degraded else f"dual_recall→RRF_top{self.k}"
            )
        return out

    def _vector_queries(self, query: str) -> list[tuple[str, str, int]]:
        queries = [("vector", query, self.vector_k)]
        keyword_query = build_keyword_query(query)
        if keyword_query and keyword_query != query:
            queries.append(("keyword_rewrite_vector", keyword_query, max(self.k, 15)))
        if ENABLE_HYDE:
            queries.append(("hyde_vector", build_hyde_query(query), max(self.k, 15)))
        return queries

    def _vector_search(self, query: str, k: int) -> list[tuple[Document, float]]:
        vectorstore = self._get_vectorstore()
        if vectorstore is None:
            return []
        metadata_filter = self._doc_type_filter()
        if metadata_filter:
            return vectorstore.similarity_search_with_score(query, k=k, filter=metadata_filter)
        return vectorstore.similarity_search_with_score(query, k=k)

    def _doc_type_filter(self) -> dict | None:
        if not self.doc_types:
            return None
        if len(self.doc_types) == 1:
            return {"doc_type": self.doc_types[0]}
        return {"doc_type": {"$in": self.doc_types}}

    @staticmethod
    def _doc_key(doc: Document) -> str:
        return doc.metadata.get("chunk_id") or f"{doc.metadata.get('source_name', '')}:{doc.page_content[:40]}"

    @staticmethod
    def _normalize_vector_score(score: float) -> float:
        if score <= 1:
            return max(0.0, min(1.0, score))
        return 1 / (1 + score)

    @staticmethod
    def _metadata_boost(doc: Document, query: str) -> float:
        """Token-overlap boost on source/section/doc_type vs the query.

        Returns a value in [0, 1] proportional to how many distinct query tokens
        appear in the doc's metadata. Section title overlap counts double because
        it strongly indicates a thematically aligned chunk (e.g. "Strategic
        Suppliers" matching a query about strategic supplier policy).
        """
        query_tokens = {tok for tok in tokenize(query) if len(tok) >= 3}
        if not query_tokens:
            return 0.0

        meta_text = " ".join(
            [
                str(doc.metadata.get("source_name", "")),
                str(doc.metadata.get("doc_type", "")),
            ]
        )
        meta_tokens = set(tokenize(meta_text))
        section_tokens = set(tokenize(str(doc.metadata.get("section_title", ""))))
        section_overlap = len(query_tokens & section_tokens)
        meta_overlap = len(query_tokens & meta_tokens)

        score = (2 * section_overlap + meta_overlap) / max(len(query_tokens), 1)

        if doc.metadata.get("source_name") and re.search(
            re.escape(str(doc.metadata.get("source_name")).split(".")[0]),
            query,
            flags=re.IGNORECASE,
        ):
            score += 0.5

        return min(score, 1.0)
