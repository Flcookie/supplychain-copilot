"""Export low-confidence / error traces as unlabeled router eval candidates.

Workflow (observability + badcase-driven iteration, not auto-learning):

  1. ``python -m eval.badcase_export``
  2. Fill ``expected_intent`` / ``expected_ambiguity_type`` by hand
  3. Append labeled rows to ``eval/datasets/router_heldout.json``
  4. ``python -m eval.run_router_eval --dataset eval/datasets/router_heldout.json --mode override``
  5. If a real pattern shows up, add a rule in ``core/router_overrides.py``
     tagged ``# tuned from badcase batch YYYY-MM-DD``
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from observability.metrics import LOW_CONFIDENCE_THRESHOLD, traces_in_window
from observability.store import get_store

DEFAULT_OUT = os.path.join(ROOT, "eval", "datasets", "badcase_unlabeled.json")


def select_badcases(
    traces: list[dict[str, Any]],
    *,
    confidence_max: float = LOW_CONFIDENCE_THRESHOLD,
    include_clarification: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in traces:
        conf = row.get("confidence")
        low_conf = isinstance(conf, (int, float)) and float(conf) < confidence_max
        has_error = bool(row.get("error"))
        is_clarify = bool(row.get("ambiguity_type")) if include_clarification else False
        if not (low_conf or has_error or is_clarify):
            continue
        reasons: list[str] = []
        if has_error:
            reasons.append("error")
        if low_conf:
            reasons.append("low_confidence")
        if is_clarify:
            reasons.append("clarification")
        query = (row.get("query") or "").strip()
        if query.lower().startswith("resume:"):
            continue
        selected.append(
            {
                "id": f"trace-{str(row.get('id') or '')[:8]}",
                "trace_id": row.get("id"),
                "timestamp": row.get("timestamp"),
                "question": query,
                "pred_intent": row.get("intent"),
                "confidence": conf,
                "pred_ambiguity_type": row.get("ambiguity_type"),
                "review_status": row.get("review_status"),
                "human_approval_required": row.get("human_approval_required"),
                "error": row.get("error"),
                "export_reason": reasons,
                "expected_intent": None,
                "expected_ambiguity_type": None,
                "notes": "",
            }
        )
        if len(selected) >= limit:
            break
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Export unlabeled router badcases from traces.db")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--hours", type=float, default=24 * 30)
    parser.add_argument("--confidence-max", type=float, default=LOW_CONFIDENCE_THRESHOLD)
    parser.add_argument("--include-clarification", action="store_true")
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()

    traces = traces_in_window(get_store(), hours=args.hours)
    cases = select_badcases(
        traces,
        confidence_max=args.confidence_max,
        include_clarification=args.include_clarification,
        limit=args.limit,
    )
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "traces.db",
        "count": len(cases),
        "instructions": (
            "Label expected_intent / expected_ambiguity_type, then append to "
            "eval/datasets/router_heldout.json. Do not copy these rows into "
            "ratti_eval_25.json — that set is the original 25-question ladder."
        ),
        "cases": cases,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Exported {len(cases)} unlabeled badcases → {args.out}")


if __name__ == "__main__":
    main()
