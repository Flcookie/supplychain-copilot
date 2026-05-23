import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, UTC

import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.qualification_rules import detect_qualification_checklist_intent


DATASET_PATH = os.path.join(ROOT_DIR, "eval", "datasets", "router_eval.json")
RESULT_DIR = os.path.join(ROOT_DIR, "eval", "results")


@dataclass
class RouterOutput:
    intent: str
    confidence: float
    ambiguity_type: str | None
    reason: str


def baseline_router(question: str) -> RouterOutput:
    q = question.lower()
    intent = "policy_qa"
    if any(k in q for k in ["otd", "otif", "kpi", "performance", "compare", "vs", "准时交", "绩效", "比较"]):
        intent = "kpi_query"
    if (any(k in q for k in ["delay", "risk", "impact", "延迟", "晚到", "中断", "风险"]) and "if" in q) or "如果" in q:
        intent = "scenario_analysis"
    return RouterOutput(intent=intent, confidence=0.0, ambiguity_type=None, reason="baseline keyword routing")


def optimized_router(question: str) -> RouterOutput:
    q = question.lower()
    if detect_qualification_checklist_intent(question):
        return RouterOutput(
            intent="qualification_checklist",
            confidence=0.93,
            ambiguity_type=None,
            reason="supplier qualification checklist keywords",
        )
    ambiguity_type = None
    if any(k in q for k in ["they", "their", "this supplier", "those vendors", "他们", "这家"]):
        ambiguity_type = "coreference"
    elif ("policy" in q or "标准" in q) and any(k in q for k in ["performance", "kpi", "交货率", "表现"]):
        ambiguity_type = "composite_intent"
    elif any(k in q for k in ["trend", "最近", "last", "performance", "delivery"]) and not any(
        k in q for k in ["alpha", "beta", "gamma", "delta", "month", "quarter", "year", "三个月", "全年"]
    ):
        ambiguity_type = "missing_entity"

    if any(k in q for k in ["if", "如果", "risk", "disruption", "impact", "延迟", "晚到", "中断"]):
        intent = "scenario_analysis"
        confidence = 0.9 if ambiguity_type is None else 0.78
    elif any(k in q for k in ["otd", "otif", "kpi", "performance", "compare", "vs", "准时", "交货率", "表现", "比较"]):
        intent = "kpi_query"
        confidence = 0.92 if ambiguity_type is None else 0.8
    else:
        intent = "policy_qa"
        confidence = 0.9 if ambiguity_type is None else 0.82

    return RouterOutput(
        intent=intent,
        confidence=confidence,
        ambiguity_type=ambiguity_type,
        reason="optimized router with ambiguity and confidence",
    )


def evaluate(router_fn, samples):
    outputs = []
    intent_hits = 0
    ambiguity_hits = 0
    fallback_count = 0
    clarification_count = 0

    for sample in samples:
        out = router_fn(sample["question"])
        intent_ok = out.intent == sample["expected_intent"]
        ambiguity_ok = out.ambiguity_type == sample["expected_ambiguity_type"]
        needs_clarify = out.ambiguity_type is not None
        is_fallback = out.ambiguity_type is None and out.confidence < 0.75

        intent_hits += int(intent_ok)
        ambiguity_hits += int(ambiguity_ok)
        clarification_count += int(needs_clarify)
        fallback_count += int(is_fallback)

        outputs.append(
            {
                "id": sample["id"],
                "question": sample["question"],
                "expected_intent": sample["expected_intent"],
                "pred_intent": out.intent,
                "expected_ambiguity_type": sample["expected_ambiguity_type"],
                "pred_ambiguity_type": out.ambiguity_type,
                "confidence": out.confidence,
                "intent_ok": intent_ok,
                "ambiguity_ok": ambiguity_ok,
                "needs_clarification": needs_clarify,
                "rag_fallback": is_fallback,
                "reason": out.reason,
            }
        )

    n = len(samples)
    return {
        "samples": n,
        "intent_accuracy": round(intent_hits / n, 4),
        "ambiguity_accuracy": round(ambiguity_hits / n, 4),
        "clarification_trigger_rate": round(clarification_count / n, 4),
        "rag_fallback_rate": round(fallback_count / n, 4),
        "details": outputs,
    }


def write_report(baseline, optimized):
    os.makedirs(RESULT_DIR, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(RESULT_DIR, f"router_eval_{ts}.json")
    md_path = os.path.join(RESULT_DIR, f"router_eval_{ts}.md")

    payload = {"baseline": baseline, "optimized": optimized}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    md = []
    md.append("# Router A/B Evaluation")
    md.append("")
    md.append(f"- Dataset: `{DATASET_PATH}`")
    md.append(f"- Samples: {optimized['samples']}")
    md.append("")
    md.append("## Metrics")
    md.append("")
    md.append(f"- Baseline intent accuracy: {baseline['intent_accuracy']:.2%}")
    md.append(f"- Optimized intent accuracy: {optimized['intent_accuracy']:.2%}")
    md.append(f"- Baseline ambiguity accuracy: {baseline['ambiguity_accuracy']:.2%}")
    md.append(f"- Optimized ambiguity accuracy: {optimized['ambiguity_accuracy']:.2%}")
    md.append(f"- Optimized clarification trigger rate: {optimized['clarification_trigger_rate']:.2%}")
    md.append(f"- Optimized RAG fallback rate: {optimized['rag_fallback_rate']:.2%}")
    md.append("")
    md.append("## Notes")
    md.append("")
    md.append("- Baseline intentionally has no ambiguity detection and no confidence.")
    md.append("- Optimized logic models ambiguity-first, confidence-second decision policy.")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    return json_path, md_path


def main():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        samples = json.load(f)

    baseline = evaluate(baseline_router, samples)
    optimized = evaluate(optimized_router, samples)
    json_path, md_path = write_report(baseline, optimized)

    print("Evaluation complete.")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")


if __name__ == "__main__":
    main()
