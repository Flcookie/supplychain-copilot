"""RAGAS-style Policy QA evaluation (Context Precision/Recall, Faithfulness, Answer Relevance).

Does NOT require the `ragas` package — implements the same four metrics with an LLM judge
plus retrieval heuristics against expected sources / answer points.

Usage:
  uv run python eval/run_ragas_eval.py --limit 20
  uv run python eval/run_ragas_eval.py --offline-only   # retrieval heuristics only, no LLM judge
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from statistics import mean
from typing import Any

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_DATASET = os.path.join(ROOT_DIR, "eval", "datasets", "rag_eval.json")
RESULT_DIR = os.path.join(ROOT_DIR, "eval", "results")

RAGAS_JUDGE_PROMPT = """You evaluate a RAG answer with RAGAS-style metrics.
Return strict JSON only:
{{
  "context_precision": {{"score": 0.0-1.0, "reason": "..."}},
  "context_recall": {{"score": 0.0-1.0, "reason": "..."}},
  "faithfulness": {{"score": 0.0-1.0, "reason": "..."}},
  "answer_relevance": {{"score": 0.0-1.0, "reason": "..."}}
}}

Definitions:
- context_precision: fraction of retrieved chunks that are useful for answering the question.
- context_recall: fraction of expected answer points supported by the retrieved context.
- faithfulness: fraction of answer claims that are grounded in the retrieved context (no hallucination).
- answer_relevance: how directly the answer addresses the user question.

Question:
{question}

Expected answer points:
{expected_answer_points}

Expected sources:
{expected_sources}

Retrieved context (truncated):
{context}

Assistant answer:
{answer}
"""


def _safe_json_load(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def _source_names(result: dict[str, Any]) -> list[str]:
    names: list[str] = []
    evidence = result.get("evidence") or {}
    for source in evidence.get("sources") or []:
        if source.get("source_name"):
            names.append(os.path.basename(str(source["source_name"])))
    for source in result.get("retrieved_docs") or []:
        if source.get("source"):
            names.append(os.path.basename(str(source["source"])))
    return list(dict.fromkeys(names))


def _context_text(result: dict[str, Any], limit: int = 6000) -> str:
    chunks: list[str] = []
    for doc in result.get("retrieved_docs") or []:
        chunks.append(doc.get("content") or "")
    evidence = result.get("evidence") or {}
    for source in evidence.get("sources") or []:
        preview = source.get("content_preview") or ""
        if preview:
            chunks.append(preview)
    text = "\n---\n".join(chunks)
    return text[:limit]


def _heuristic_context_precision(expected_sources: list[str], actual_sources: list[str]) -> float:
    if not actual_sources:
        return 0.0 if expected_sources else 1.0
    expected = [os.path.basename(s).lower() for s in expected_sources]
    hits = 0
    for actual in actual_sources:
        base = os.path.basename(actual).lower()
        if any(exp in base or base in exp for exp in expected):
            hits += 1
    return round(hits / len(actual_sources), 4)


def _heuristic_context_recall(expected_sources: list[str], actual_sources: list[str]) -> float:
    if not expected_sources:
        return 1.0
    expected = [os.path.basename(s).lower() for s in expected_sources]
    actual = [os.path.basename(s).lower() for s in actual_sources]
    hits = 0
    for exp in expected:
        if any(exp in a or a in exp for a in actual):
            hits += 1
    return round(hits / len(expected), 4)


def _heuristic_answer_point_recall(expected_points: list[str], answer: str) -> float:
    if not expected_points:
        return 1.0
    lower = (answer or "").lower()
    hits = sum(1 for p in expected_points if p.lower() in lower or any(tok in lower for tok in p.lower().split()[:2]))
    return round(hits / len(expected_points), 4)


def _llm_ragas_scores(
    *,
    question: str,
    expected_answer_points: list[str],
    expected_sources: list[str],
    context: str,
    answer: str,
) -> dict[str, Any]:
    from langchain_openai import ChatOpenAI

    model = os.getenv("JUDGE_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))
    raw = ChatOpenAI(model=model, temperature=0).invoke(
        RAGAS_JUDGE_PROMPT.format(
            question=question,
            expected_answer_points=json.dumps(expected_answer_points, ensure_ascii=False),
            expected_sources=json.dumps(expected_sources, ensure_ascii=False),
            context=context,
            answer=answer,
        )
    ).content
    parsed = _safe_json_load(raw if isinstance(raw, str) else str(raw))
    out: dict[str, Any] = {}
    for key in ["context_precision", "context_recall", "faithfulness", "answer_relevance"]:
        block = parsed.get(key) or {}
        try:
            score = float(block.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        out[key] = {"score": max(0.0, min(1.0, score)), "reason": block.get("reason", "")}
    return out


def evaluate(
    samples: list[dict[str, Any]],
    *,
    offline_only: bool = False,
) -> dict[str, Any]:
    from graph.graph import build_graph
    from graph.invoke import invoke_graph

    graph = build_graph()
    details: list[dict[str, Any]] = []

    for sample in samples:
        started = time.perf_counter()
        # Force policy path when labeled; still goes through router unless baseline_mode.
        result = invoke_graph(
            graph,
            {
                "question": sample["question"],
                "response_language": sample.get("lang") or "en",
                "baseline_mode": True,
                "intent": "policy_qa",
                "confidence": 1.0,
            },
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        actual_sources = _source_names(result)
        expected_sources = sample.get("expected_sources") or []
        expected_points = sample.get("expected_answer_points") or []
        answer = result.get("answer") or ""
        context = _context_text(result)

        heur = {
            "context_precision": _heuristic_context_precision(expected_sources, actual_sources),
            "context_recall": _heuristic_context_recall(expected_sources, actual_sources),
            "answer_point_overlap": _heuristic_answer_point_recall(expected_points, answer),
        }

        judge: dict[str, Any] = {}
        if not offline_only:
            try:
                judge = _llm_ragas_scores(
                    question=sample["question"],
                    expected_answer_points=expected_points,
                    expected_sources=expected_sources,
                    context=context,
                    answer=answer,
                )
            except Exception as exc:  # noqa: BLE001
                judge = {"error": str(exc)}

        details.append(
            {
                "id": sample.get("id"),
                "question": sample["question"],
                "expected_sources": expected_sources,
                "actual_sources": actual_sources,
                "latency_ms": latency_ms,
                "injection_blocked": bool(result.get("injection_blocked")),
                "answer": answer,
                "heuristics": heur,
                "ragas": judge,
            }
        )

    def _avg(path: str) -> float | None:
        vals = []
        for item in details:
            cur: Any = item
            for part in path.split("."):
                if not isinstance(cur, dict):
                    cur = None
                    break
                cur = cur.get(part)
            if isinstance(cur, (int, float)):
                vals.append(float(cur))
        return round(mean(vals), 4) if vals else None

    metrics = {
        "samples": len(details),
        "offline_only": offline_only,
        "heuristic_context_precision": _avg("heuristics.context_precision"),
        "heuristic_context_recall": _avg("heuristics.context_recall"),
        "heuristic_answer_point_overlap": _avg("heuristics.answer_point_overlap"),
        "ragas_context_precision": _avg("ragas.context_precision.score"),
        "ragas_context_recall": _avg("ragas.context_recall.score"),
        "ragas_faithfulness": _avg("ragas.faithfulness.score"),
        "ragas_answer_relevance": _avg("ragas.answer_relevance.score"),
        "avg_latency_ms": round(mean([d["latency_ms"] for d in details]), 2) if details else 0,
    }
    return {"metrics": metrics, "details": details}


def write_report(payload: dict[str, Any], *, label: str) -> tuple[str, str]:
    os.makedirs(RESULT_DIR, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(RESULT_DIR, f"ragas_eval_{label}_{ts}.json")
    md_path = os.path.join(RESULT_DIR, f"ragas_eval_{label}_{ts}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    m = payload["metrics"]
    lines = [
        "# RAGAS-style Policy QA Evaluation",
        "",
        f"- Label: `{label}`",
        f"- Samples: {m['samples']}",
        f"- Offline only: {m['offline_only']}",
        "",
        "## Metrics (0–1)",
        "",
        f"- Heuristic Context Precision: {m['heuristic_context_precision']}",
        f"- Heuristic Context Recall: {m['heuristic_context_recall']}",
        f"- Heuristic Answer-point Overlap: {m['heuristic_answer_point_overlap']}",
        f"- RAGAS Context Precision: {m['ragas_context_precision']}",
        f"- RAGAS Context Recall: {m['ragas_context_recall']}",
        f"- RAGAS Faithfulness: {m['ragas_faithfulness']}",
        f"- RAGAS Answer Relevance: {m['ragas_answer_relevance']}",
        f"- Avg latency: {m['avg_latency_ms']} ms",
        "",
        "## Resume one-liner",
        "",
        (
            f"Policy QA RAGAS-style eval on {m['samples']} cases: "
            f"Faithfulness={m['ragas_faithfulness']}, "
            f"Context Recall={m['ragas_context_recall']}, "
            f"Answer Relevance={m['ragas_answer_relevance']}."
            if m["ragas_faithfulness"] is not None
            else (
                f"Policy QA retrieval heuristics on {m['samples']} cases: "
                f"Context Precision={m['heuristic_context_precision']}, "
                f"Context Recall={m['heuristic_context_recall']}."
            )
        ),
    ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--label", default="policy")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offline-only", action="store_true")
    parser.add_argument("--intent", default="policy_qa")
    args = parser.parse_args()

    with open(args.dataset, encoding="utf-8") as f:
        samples = json.load(f)
    if args.intent:
        samples = [s for s in samples if s.get("intent") == args.intent]
    if args.limit:
        samples = samples[: args.limit]

    payload = evaluate(samples, offline_only=args.offline_only)
    json_path, md_path = write_report(payload, label=args.label)
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
