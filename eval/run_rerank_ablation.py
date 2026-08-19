"""Same-pool rerank ablation: Noop vs Cross-Encoder (fixture or live retriever).

Fixture (offline, CI):
  uv run python eval/run_rerank_ablation.py

Live (needs Pinecone + optional CE weights / OpenAI):
  uv run python eval/run_rerank_ablation.py --live --backends none,cross_encoder
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime

from langchain_core.documents import Document

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rag.rerank import CrossEncoderReranker, NoopReranker

FIXTURE = os.path.join(ROOT, "eval", "datasets", "rerank_ablation_pool.json")
RESULT_DIR = os.path.join(ROOT, "eval", "results")
RAG_EVAL = os.path.join(ROOT, "eval", "datasets", "rag_eval.json")


def _hit_at_k(expected: list[str], ranked_sources: list[str], k: int) -> bool:
    gold = {os.path.basename(name).lower() for name in expected}
    for source in ranked_sources[:k]:
        base = os.path.basename(source).lower()
        if any(g in base or base in g for g in gold):
            return True
    return False


def _pool_docs(raw_pool: list[dict]) -> list[Document]:
    docs = []
    for idx, item in enumerate(raw_pool, start=1):
        docs.append(
            Document(
                page_content=item["content"],
                metadata={"source_name": item["source"], "source": item["source"], "rrf_rank": idx},
            )
        )
    return docs


def evaluate_fixture(top_k: int = 5) -> dict:
    payload = json.loads(open(FIXTURE, encoding="utf-8").read())
    top_k = int(payload.get("top_k") or top_k)
    noop = NoopReranker()
    ce = CrossEncoderReranker(model_name="fixture-lexical")

    class _LexicalCE:
        def predict(self, pairs):
            scores = []
            for query, text in pairs:
                q = (query or "").lower()
                t = (text or "").lower()
                scores.append(sum(1.0 for token in q.split() if token in t))
            return scores

    ce._ensure_model = lambda: _LexicalCE()  # type: ignore[method-assign]
    rows = []
    noop_hits = 0
    ce_hits = 0
    for case in payload["cases"]:
        docs = _pool_docs(case["pool"])
        expected = case["expected_sources"]
        none_ranked = noop.rerank(case["question"], docs, top_k=top_k)
        ce_ranked = ce.rerank(case["question"], docs, top_k=top_k)
        none_ok = _hit_at_k(expected, [d.metadata["source"] for d in none_ranked], top_k)
        ce_ok = _hit_at_k(expected, [d.metadata["source"] for d in ce_ranked], top_k)
        noop_hits += int(none_ok)
        ce_hits += int(ce_ok)
        rows.append(
            {
                "id": case["id"],
                "noop_recall_at_k": none_ok,
                "ce_recall_at_k": ce_ok,
                "noop_top": [d.metadata["source"] for d in none_ranked],
                "ce_top": [d.metadata["source"] for d in ce_ranked],
            }
        )
    n = len(payload["cases"])
    return {
        "mode": "fixture",
        "samples": n,
        "top_k": top_k,
        "noop_recall_at_k": round(noop_hits / n, 4) if n else 0.0,
        "cross_encoder_recall_at_k": round(ce_hits / n, 4) if n else 0.0,
        "details": rows,
        "note": "Lexical stand-in for CE on a frozen RRF-shaped pool. Live CE needs --live.",
    }


def evaluate_live(backends: list[str], top_k: int = 5) -> dict:
    from rag.hybrid_retriever import HybridRetriever
    from rag.rerank import OpenAIEmbeddingReranker, get_reranker

    samples = json.loads(open(RAG_EVAL, encoding="utf-8").read())
    policy = [s for s in samples if s.get("intent") == "policy_qa"]
    retriever = HybridRetriever(k=20, rerank_pool=20, reranker=None)
    backend_hits: dict[str, int] = {name: 0 for name in backends}
    details = []
    for sample in policy:
        pool = retriever.invoke(sample["question"])
        expected = sample.get("expected_sources") or []
        row = {"id": sample["id"], "question": sample["question"]}
        for name in backends:
            if name in {"none", "noop"}:
                ranked = NoopReranker().rerank(sample["question"], pool, top_k=top_k)
            elif name in {"cross_encoder", "ce"}:
                ranked = get_reranker(force_reload=True).rerank(sample["question"], pool, top_k=top_k)
            elif name in {"embedding", "openai"}:
                ranked = OpenAIEmbeddingReranker().rerank(sample["question"], pool, top_k=top_k)
            else:
                raise ValueError(name)
            sources = [
                d.metadata.get("source_name") or d.metadata.get("source") or "" for d in ranked
            ]
            hit = _hit_at_k(expected, sources, top_k)
            backend_hits[name] += int(hit)
            row[f"{name}_recall_at_{top_k}"] = hit
        details.append(row)
    n = len(policy)
    metrics = {
        "mode": "live",
        "samples": n,
        "top_k": top_k,
        "details": details,
    }
    for name, hits in backend_hits.items():
        metrics[f"{name}_recall_at_{top_k}"] = round(hits / n, 4) if n else 0.0
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--backends", default="none,cross_encoder")
    args = parser.parse_args()
    if args.live:
        report = evaluate_live([b.strip() for b in args.backends.split(",") if b.strip()])
    else:
        report = evaluate_fixture()
    os.makedirs(RESULT_DIR, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out = os.path.join(RESULT_DIR, f"rerank_ablation_{ts}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    printable = {k: v for k, v in report.items() if k != "details"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
