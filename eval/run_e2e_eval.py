"""Intent-dispatched E2E judges: KPI groundedness + HITL action safety (rule-based).

Default path is offline and deterministic (no LLM):
  uv run python -m eval.run_e2e_eval

Optional LLM RAG dimensions can be mixed in later; they are normalized 0-1 so
E2E Score = mean(applicable judges) stays on one scale.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from statistics import mean
from typing import Any

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from eval.judges import dispatch_e2e_judges

DEFAULT_DATASET = os.path.join(ROOT, "eval", "datasets", "e2e_rule_cases.json")
RESULT_DIR = os.path.join(ROOT, "eval", "results")


def evaluate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    details = []
    for case in cases:
        judged = dispatch_e2e_judges(
            intent=case.get("intent") or "unknown",
            answer=case.get("answer") or "",
            sql_result=case.get("sql_result"),
            needs_hitl=bool(case.get("needs_hitl")),
            approval_decision=case.get("approval_decision"),
        )
        details.append(
            {
                "id": case.get("id"),
                "question": case.get("question"),
                **judged,
            }
        )
    scores = [row["e2e_score"] for row in details if row.get("e2e_score") is not None]
    return {
        "samples": len(details),
        "e2e_score": round(mean(scores), 4) if scores else None,
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rule-based E2E judges (KPI + HITL safety)")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    args = parser.parse_args()

    with open(args.dataset, encoding="utf-8") as f:
        cases = json.load(f)

    report = evaluate_cases(cases)
    os.makedirs(RESULT_DIR, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(RESULT_DIR, f"e2e_judged_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"E2E score: {report['e2e_score']}  ({report['samples']} cases)")
    print(f"Report: {out_path}")
    for row in report["details"]:
        flag = "OK" if (row.get("e2e_score") or 0) >= 0.99 else "MIX"
        print(f"  [{flag}] {row.get('id')} intent={row.get('intent')} score={row.get('e2e_score')}")


if __name__ == "__main__":
    main()
