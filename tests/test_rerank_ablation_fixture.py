"""Same-pool rerank: Noop misses gold outside Top5; CE-style scores promote it."""

from __future__ import annotations

import json
import os

from langchain_core.documents import Document

from rag.rerank import CrossEncoderReranker, NoopReranker

ROOT = os.path.dirname(os.path.dirname(__file__))
FIXTURE = os.path.join(ROOT, "eval", "datasets", "rerank_ablation_pool.json")


def test_same_pool_ce_recovers_gold_that_noop_misses(monkeypatch):
    payload = json.loads(open(FIXTURE, encoding="utf-8").read())
    case = payload["cases"][0]
    top_k = int(payload["top_k"])
    docs = [
        Document(page_content=item["content"], metadata={"source": item["source"], "rrf_rank": i})
        for i, item in enumerate(case["pool"], start=1)
    ]
    gold = case["expected_sources"][0]
    noop_top = [d.metadata["source"] for d in NoopReranker().rerank(case["question"], docs, top_k=top_k)]
    assert gold not in noop_top

    reranker = CrossEncoderReranker(model_name="fake-bge")

    class _FakeCE:
        def predict(self, pairs):
            return [0.9 if "ESG" in text else 0.1 for _, text in pairs]

    monkeypatch.setattr(reranker, "_ensure_model", lambda: _FakeCE())
    ce_top = [d.metadata["source"] for d in reranker.rerank(case["question"], docs, top_k=top_k)]
    assert gold in ce_top
    assert ce_top[0] == gold
