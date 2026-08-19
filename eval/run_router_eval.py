import argparse
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
from core.router_overrides import (
    apply_lifecycle_router_overrides,
    is_overbroad_data_request,
    is_unresolved_coreference,
)


def _has_keyword(text: str, keyword: str) -> bool:
    """Match CJK/phrases by substring; ASCII tokens by word boundary.

    Prevents ``if`` from firing inside ``certificates`` / ``certificate``.
    """
    if not keyword:
        return False
    if any("\u4e00" <= ch <= "\u9fff" for ch in keyword) or " " in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text, flags=re.IGNORECASE) is not None


DEFAULT_DATASET = os.path.join(ROOT_DIR, "eval", "datasets", "ratti_eval_25.json")
HELDOUT_DATASET = os.path.join(ROOT_DIR, "eval", "datasets", "router_heldout.json")
HELDOUT_SEMANTIC_DATASET = os.path.join(ROOT_DIR, "eval", "datasets", "router_heldout_semantic.json")
LEGACY_DATASET = os.path.join(ROOT_DIR, "eval", "datasets", "router_eval.json")
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
    if (
        any(k in q for k in ["delay", "risk", "impact", "延迟", "晚到", "中断", "风险"])
        and _has_keyword(q, "if")
    ) or "如果" in q:
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
    if "blacklist" in q or ("review" in q and "high risk" in q):
        return RouterOutput(
            intent="risk_scenario",
            confidence=0.9,
            ambiguity_type=None,
            reason="risk scenario keywords",
        )
    if re.search(r"\bsup\d{3}\b", q) and ("rating" in q or " c rating" in q or "why did" in q):
        return RouterOutput(
            intent="vendor_rating_explanation",
            confidence=0.9,
            ambiguity_type=None,
            reason="vendor rating explanation keywords",
        )
    if "vendor rating formula" in q or ("formula" in q and "yarn" in q):
        return RouterOutput(
            intent="vendor_rating_explanation",
            confidence=0.88,
            ambiguity_type=None,
            reason="rating formula question",
        )
    if is_overbroad_data_request(question):
        return RouterOutput(
            intent="policy_qa",
            confidence=0.7,
            ambiguity_type="overbroad_data_request",
            reason="overbroad data request",
        )
    ambiguity_type = None
    if is_unresolved_coreference(question):
        ambiguity_type = "coreference"
    elif ("policy" in q or "标准" in q) and any(k in q for k in ["performance", "kpi", "交货率", "表现"]):
        ambiguity_type = "composite_intent"

    if any(
        _has_keyword(q, k)
        for k in ["if", "如果", "risk", "disruption", "impact", "延迟", "single sourcing", "quality issues"]
    ):
        intent = "risk_scenario"
        confidence = 0.9 if ambiguity_type is None else 0.78
    elif any(k in q for k in ["otd", "otif", "kpi", "performance", "compare", "vs", "准时", "交货率", "defect", "spend", "esg", "sup0", "next step", "expire", "rank"]):
        intent = "kpi_query"
        confidence = 0.92 if ambiguity_type is None else 0.8
    else:
        intent = "policy_qa"
        confidence = 0.9 if ambiguity_type is None else 0.82

    return RouterOutput(
        intent=intent,
        confidence=confidence,
        ambiguity_type=ambiguity_type,
        reason="optimized router with Ratti lifecycle intents",
    )


def override_router(question: str) -> RouterOutput:
    """Heuristic router plus deterministic lifecycle overrides (no LLM)."""
    base = optimized_router(question)
    parsed = {
        "intent": base.intent,
        "confidence": base.confidence,
        "ambiguity_type": base.ambiguity_type,
        "human_approval_required": False,
        "reason": base.reason,
    }
    out = apply_lifecycle_router_overrides(parsed, question)
    return RouterOutput(
        intent=out.get("intent", base.intent),
        confidence=float(out.get("confidence", base.confidence) or 0.0),
        ambiguity_type=out.get("ambiguity_type"),
        reason=out.get("reason") or "heuristic + deterministic override",
    )


def llm_router(question: str) -> RouterOutput:
    from graph.nodes import router_node

    state = router_node({"question": question})
    return RouterOutput(
        intent=state.get("intent", "policy_qa"),
        confidence=float(state.get("confidence", 0.0)),
        ambiguity_type=state.get("ambiguity_type"),
        reason=state.get("reason", "llm router"),
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


def write_report(baseline, optimized, dataset_path: str, label: str = "optimized"):
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
    md.append(f"- Dataset: `{dataset_path}`")
    md.append(f"- Mode: {label}")
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
    parser = argparse.ArgumentParser(description="Router evaluation for Supplier Lifecycle Copilot")
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help="Path to eval JSON (default: ratti_eval_25.json). Use router_heldout.json for unseen paraphrases.",
    )
    parser.add_argument(
        "--heldout",
        action="store_true",
        help="Shortcut for --dataset eval/datasets/router_heldout.json",
    )
    parser.add_argument(
        "--heldout-semantic",
        action="store_true",
        help="Shortcut for --dataset eval/datasets/router_heldout_semantic.json (004/005/010 paraphrases)",
    )
    parser.add_argument(
        "--mode",
        choices=["heuristic", "override", "llm", "llm+override"],
        default="heuristic",
        help=(
            "heuristic=keyword router; override=heuristic+deterministic overrides; "
            "llm / llm+override=live router_node (LLM structured output + the same overrides)"
        ),
    )
    args = parser.parse_args()
    if args.heldout_semantic:
        dataset_path = HELDOUT_SEMANTIC_DATASET
    elif args.heldout:
        dataset_path = HELDOUT_DATASET
    else:
        dataset_path = args.dataset
    mode = "llm" if args.mode == "llm+override" else args.mode

    with open(dataset_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    baseline = evaluate(baseline_router, samples)
    routers = {
        "heuristic": optimized_router,
        "override": override_router,
        "llm": llm_router,
    }
    optimized = evaluate(routers[mode], samples)
    json_path, md_path = write_report(baseline, optimized, dataset_path, label=args.mode)

    print("Evaluation complete.")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")


if __name__ == "__main__":
    main()
