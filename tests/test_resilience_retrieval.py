"""Pinecone-down retrieval degrades to BM25-only instead of failing the request."""

from __future__ import annotations

from langchain_core.documents import Document

from rag.bm25_index import LocalBM25Index
from rag.hybrid_retriever import HybridRetriever


class _BoomStore:
    def similarity_search_with_score(self, *args, **kwargs):
        raise ConnectionError("pinecone unreachable")


def test_hybrid_retriever_is_lazy_and_does_not_touch_pinecone_at_init(monkeypatch):
    def boom():
        raise AssertionError("get_vectorstore should not run at init")

    monkeypatch.setattr("rag.retriever.get_vectorstore", boom)
    HybridRetriever(k=1, bm25=LocalBM25Index([]), reranker=None)


def test_pinecone_down_falls_back_to_bm25_only():
    docs = [
        Document(
            page_content="ESG scoring formula details for yarn suppliers",
            metadata={"chunk_id": "esg-1", "doc_type": "policy", "source_name": "esg.txt"},
        ),
        Document(
            page_content="Warehouse packing SOP",
            metadata={"chunk_id": "wh-1", "doc_type": "sop", "source_name": "sop.txt"},
        ),
    ]
    retriever = HybridRetriever(
        k=2,
        bm25=LocalBM25Index(docs),
        reranker=None,
        vectorstore=_BoomStore(),
    )
    out = retriever.invoke("How is ESG score calculated?")
    assert out
    assert "ESG" in out[0].page_content
    assert out[0].metadata.get("retrieval_mode") == "bm25_only"
    assert out[0].metadata.get("retrieval_degraded") is True
    assert retriever.last_degraded is True
    assert "bm25_only" in (out[0].metadata.get("retrieval_funnel") or "")
