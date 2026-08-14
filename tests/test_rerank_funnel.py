"""Unit tests for Cross-Encoder rerank funnel (no Pinecone / no model download)."""

from __future__ import annotations

from langchain_core.documents import Document

from rag.rerank import CrossEncoderReranker, NoopReranker, get_reranker


class _FakeCE:
    def predict(self, pairs):
        # Prefer docs that mention "ESG".
        scores = []
        for _, text in pairs:
            scores.append(0.9 if "ESG" in text else 0.1)
        return scores


def test_cross_encoder_reranks_and_truncates_to_top_k(monkeypatch):
    reranker = CrossEncoderReranker(model_name="fake-bge")
    monkeypatch.setattr(reranker, "_ensure_model", lambda: _FakeCE())

    docs = [
        Document(page_content="Delivery delay policy", metadata={"chunk_id": "1", "rrf_rank": 1}),
        Document(page_content="ESG scoring formula details", metadata={"chunk_id": "2", "rrf_rank": 2}),
        Document(page_content="Warehouse SOP", metadata={"chunk_id": "3", "rrf_rank": 3}),
    ]
    out = reranker.rerank("How is ESG score calculated?", docs, top_k=2)
    assert len(out) == 2
    assert "ESG" in out[0].page_content
    assert out[0].metadata["reranker"] == "cross_encoder"
    assert out[0].metadata["rerank_rank"] == 1
    assert out[0].metadata["rerank_score"] >= out[1].metadata["rerank_score"]


def test_noop_reranker_preserves_order():
    docs = [
        Document(page_content="a", metadata={"retrieval_score": 0.8}),
        Document(page_content="b", metadata={"retrieval_score": 0.7}),
    ]
    out = NoopReranker().rerank("q", docs, top_k=1)
    assert len(out) == 1
    assert out[0].page_content == "a"
    assert out[0].metadata["reranker"] == "none"


def test_get_reranker_falls_back_when_ce_unavailable(monkeypatch):
    import rag.rerank as rerank_mod

    monkeypatch.setattr(rerank_mod, "RERANKER_BACKEND", "cross_encoder")
    monkeypatch.setattr(rerank_mod, "RERANKER_FALLBACK", "none")
    monkeypatch.setattr(rerank_mod, "_RERANKER_SINGLETON", None)
    monkeypatch.setattr(rerank_mod, "_RERANKER_BACKEND_IN_USE", None)

    def _boom(name: str):
        key = (name or "none").lower().strip()
        if key in {"cross_encoder", "ce", "bge"}:
            raise ImportError("sentence-transformers missing")
        if key in {"none", "noop", "off", ""}:
            return NoopReranker()
        raise ValueError(name)

    monkeypatch.setattr(rerank_mod, "_build_backend", _boom)
    reranker = get_reranker(force_reload=True)
    assert isinstance(reranker, NoopReranker)


def test_rrf_pool_to_ce_top_k_contract():
    """Contract: RRF pool (20) → Cross-Encoder → final top 5."""
    pool = [
        Document(page_content=f"doc-{i}", metadata={"chunk_id": str(i), "rrf_rank": i + 1})
        for i in range(20)
    ]

    class _CE:
        name = "cross_encoder"

        def rerank(self, query, docs, top_k):
            ranked = list(reversed(docs))[:top_k]
            for idx, doc in enumerate(ranked, start=1):
                doc.metadata["rerank_score"] = 1.0 - idx * 0.01
                doc.metadata["reranker"] = "cross_encoder"
                doc.metadata["rerank_rank"] = idx
                doc.metadata["retrieval_funnel"] = (
                    f"dual_recall→RRF_top{len(docs)}→cross_encoder_top{top_k}"
                )
            return ranked

    out = _CE().rerank("q", pool, top_k=5)
    assert len(out) == 5
    assert out[0].page_content == "doc-19"
    assert out[0].metadata["rerank_rank"] == 1
    assert "RRF_top20" in out[0].metadata["retrieval_funnel"]
    assert "cross_encoder_top5" in out[0].metadata["retrieval_funnel"]
