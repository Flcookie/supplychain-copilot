from __future__ import annotations

import copy
import re
from typing import Any

from langchain_core.documents import Document

from core.config import ENABLE_HYDE
from rag.bm25_index import load_bm25_index, tokenize
from rag.query_expansion import build_hyde_query, build_keyword_query
from rag.retriever import get_vectorstore


# Reciprocal Rank Fusion constant. Lower => earlier ranks dominate more.
RRF_K = 60


class HybridRetriever:
    def __init__(
        self,
        *,
        k: int = 5,
        vector_k: int = 30,
        keyword_k: int = 30,
        rerank_pool: int = 20,
        doc_types: list[str] | None = None,
        reranker: Any | None = None,
    ):
        self.k = k
        self.vector_k = vector_k
        self.keyword_k = keyword_k
        self.rerank_pool = rerank_pool
        self.doc_types = doc_types
        self.reranker = reranker
        self.vectorstore = get_vectorstore()
        self.bm25 = load_bm25_index()

    def invoke(self, query: str) -> list[Document]:
        candidates: dict[str, dict[str, Any]] = {}

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
                item["vector_score"] = max(item["vector_score"], self._normalize_vector_score(score))
                item["rrf_score"] += 1.0 / (RRF_K + rank)
                item["routes"].append(route)

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
        rerank_input = fused_docs[: max(self.rerank_pool, self.k)]
        if self.reranker:
            rerank_input = self.reranker.rerank(query, rerank_input, top_k=self.k)
        return rerank_input[: self.k]

    def _vector_queries(self, query: str) -> list[tuple[str, str, int]]:
        queries = [("vector", query, self.vector_k)]
        keyword_query = build_keyword_query(query)
        if keyword_query and keyword_query != query:
            queries.append(("keyword_rewrite_vector", keyword_query, max(self.k, 15)))
        if ENABLE_HYDE:
            queries.append(("hyde_vector", build_hyde_query(query), max(self.k, 15)))
        return queries

    def _vector_search(self, query: str, k: int) -> list[tuple[Document, float]]:
        metadata_filter = self._doc_type_filter()
        if metadata_filter:
            return self.vectorstore.similarity_search_with_score(query, k=k, filter=metadata_filter)
        return self.vectorstore.similarity_search_with_score(query, k=k)

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
