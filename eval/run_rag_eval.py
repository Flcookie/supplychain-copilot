import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from statistics import mean
from typing import Any

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from eval.judges import judge_answer
from graph.graph import build_graph


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATASET_PATH = os.path.join(ROOT_DIR, "eval", "datasets", "rag_eval.json")
RESULT_DIR = os.path.join(ROOT_DIR, "eval", "results")


def _source_names_from_result(result: dict[str, Any]) -> list[str]:
    names: list[str] = []
    evidence = result.get("evidence") or {}
    for source in evidence.get("sources") or []:
        if source.get("source_name"):
            names.append(source["source_name"])
    for source in result.get("retrieved_docs") or []:
        if source.get("source"):
            names.append(os.path.basename(source["source"]))
    for citation in result.get("citations") or []:
        if citation.get("source"):
            names.append(os.path.basename(citation["source"]))
        if citation.get("type") == "sql":
            names.append("metric_definitions.txt")
    if evidence.get("sql"):
        names.append("metric_definitions.txt")
    return list(dict.fromkeys(names))


def _hit_position(expected_sources: list[str], actual_sources: list[str]) -> int | None:
    if not expected_sources:
        return None
    expected = [os.path.basename(item).lower() for item in expected_sources]
    for idx, actual in enumerate(actual_sources, start=1):
        actual_base = os.path.basename(actual).lower()
        if any(exp in actual_base or actual_base in exp for exp in expected):
            return idx
    return None


def _recall_at_k(expected_sources: list[str], actual_sources: list[str], k: int) -> bool:
    if not expected_sources:
        return True
    return _hit_position(expected_sources, actual_sources[:k]) is not None


def _avg_judge_metric(details: list[dict[str, Any]], metric: str) -> float | None:
    scores = [
        item.get("judge", {}).get(metric, {}).get("score")
        for item in details
        if item.get("judge", {}).get(metric, {}).get("score") is not None
    ]
    return round(mean(scores), 3) if scores else None


def evaluate(samples: list[dict[str, Any]], *, skip_judge: bool = False) -> dict[str, Any]:
    graph = build_graph()
    details = []
    for sample in samples:
        started = time.perf_counter()
        result = graph.invoke({"question": sample["question"], "response_language": "en"})
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        actual_sources = _source_names_from_result(result)
        hit_pos = _hit_position(sample.get("expected_sources", []), actual_sources)
        judge = {}
        if not skip_judge:
            judge = judge_answer(
                question=sample["question"],
                expected_answer_points=sample.get("expected_answer_points", []),
                answerability=bool(sample.get("answerability", True)),
                evidence=result.get("evidence") or {"citations": result.get("citations", [])},
                answer=result.get("answer", ""),
            )
        details.append(
            {
                "id": sample["id"],
                "question": sample["question"],
                "intent": sample.get("intent"),
                "difficulty": sample.get("difficulty"),
                "answerability": sample.get("answerability"),
                "expected_sources": sample.get("expected_sources", []),
                "actual_sources": actual_sources,
                "hit_position": hit_pos,
                "recall_at_3": _recall_at_k(sample.get("expected_sources", []), actual_sources, 3),
                "recall_at_5": _recall_at_k(sample.get("expected_sources", []), actual_sources, 5),
                "recall_at_10": _recall_at_k(sample.get("expected_sources", []), actual_sources, 10),
                "mrr": round(1 / hit_pos, 4) if hit_pos else 0.0,
                "latency_ms": latency_ms,
                "answer": result.get("answer", ""),
                "route": {
                    "intent": result.get("intent"),
                    "confidence": result.get("confidence"),
                    "ambiguity_type": result.get("ambiguity_type"),
                    "fallback_mode": result.get("fallback_mode"),
                },
                "evidence": result.get("evidence", {}),
                "judge": judge,
            }
        )

    metrics = {
        "samples": len(details),
        "retrieval_recall_at_3": round(mean([item["recall_at_3"] for item in details]), 4),
        "retrieval_recall_at_5": round(mean([item["recall_at_5"] for item in details]), 4),
        "retrieval_recall_at_10": round(mean([item["recall_at_10"] for item in details]), 4),
        "mrr": round(mean([item["mrr"] for item in details]), 4),
        "avg_latency_ms": round(mean([item["latency_ms"] for item in details]), 2),
        "faithfulness": _avg_judge_metric(details, "faithfulness"),
        "citation_precision": _avg_judge_metric(details, "citation_precision"),
        "answer_completeness": _avg_judge_metric(details, "answer_completeness"),
        "refusal_accuracy": _avg_judge_metric(details, "refusal_accuracy"),
    }
    return {"metrics": metrics, "details": details}


def write_report(payload: dict[str, Any], *, label: str) -> tuple[str, str]:
    os.makedirs(RESULT_DIR, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(RESULT_DIR, f"rag_eval_{label}_{ts}.json")
    md_path = os.path.join(RESULT_DIR, f"rag_eval_{label}_{ts}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    metrics = payload["metrics"]
    lines = [
        "# RAG Evaluation",
        "",
        f"- Label: `{label}`",
        f"- Dataset: `{DATASET_PATH}`",
        f"- Samples: {metrics['samples']}",
        "",
        "## Metrics",
        "",
        f"- Retrieval Recall@3: {metrics['retrieval_recall_at_3']:.2%}",
        f"- Retrieval Recall@5: {metrics['retrieval_recall_at_5']:.2%}",
        f"- Retrieval Recall@10: {metrics['retrieval_recall_at_10']:.2%}",
        f"- MRR: {metrics['mrr']:.4f}",
        f"- Avg latency: {metrics['avg_latency_ms']} ms",
        f"- Faithfulness: {metrics['faithfulness']}",
        f"- Citation precision: {metrics['citation_precision']}",
        f"- Answer completeness: {metrics['answer_completeness']}",
        f"- Refusal accuracy: {metrics['refusal_accuracy']}",
    ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return json_path, md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-judge", action="store_true")
    args = parser.parse_args()

    with open(DATASET_PATH, encoding="utf-8") as f:
        samples = json.load(f)
    if args.limit:
        samples = samples[: args.limit]
    payload = evaluate(samples, skip_judge=args.skip_judge)
    json_path, md_path = write_report(payload, label=args.label)
    print("RAG evaluation complete.")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")


if __name__ == "__main__":
    main()
