"""Run prompt-injection detector eval (no LLM). Optionally smoke Policy QA refusals.

Usage:
  uv run python eval/run_injection_eval.py
  uv run python eval/run_injection_eval.py --with-policy-node
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.prompt_injection import scan_user_input

ROOT = os.path.dirname(os.path.dirname(__file__))
DATASET = os.path.join(ROOT, "eval", "datasets", "prompt_injection_eval.json")
RESULT_DIR = os.path.join(ROOT, "eval", "results")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-policy-node", action="store_true")
    args = parser.parse_args()

    with open(DATASET, encoding="utf-8") as f:
        cases = json.load(f)

    details = []
    correct = 0
    for case in cases:
        scan = scan_user_input(case["question"])
        predicted = scan.should_refuse
        expected = bool(case["expect_refuse"])
        ok = predicted == expected
        correct += int(ok)
        row = {
            "id": case["id"],
            "expected_refuse": expected,
            "predicted_refuse": predicted,
            "correct": ok,
            "reasons": list(scan.reasons),
            "primary_attack": scan.primary_attack,
        }
        if args.with_policy_node:
            from graph.nodes import policy_qa_node

            state = policy_qa_node(
                {
                    "question": case["question"],
                    "response_language": case.get("lang") or "en",
                }
            )
            row["injection_blocked"] = bool(state.get("injection_blocked"))
            row["answer_preview"] = (state.get("answer") or "")[:180]
        details.append(row)

    metrics = {
        "samples": len(cases),
        "detector_accuracy": round(correct / len(cases), 4) if cases else 0.0,
        "attack_cases": sum(1 for c in cases if c["expect_refuse"]),
        "benign_cases": sum(1 for c in cases if not c["expect_refuse"]),
        "false_negatives": [
            d["id"] for d in details if d["expected_refuse"] and not d["predicted_refuse"]
        ],
        "false_positives": [
            d["id"] for d in details if (not d["expected_refuse"]) and d["predicted_refuse"]
        ],
    }
    payload = {"metrics": metrics, "details": details}
    os.makedirs(RESULT_DIR, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out = os.path.join(RESULT_DIR, f"injection_eval_{ts}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
