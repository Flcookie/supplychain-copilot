"""Quick helper to inspect failing samples from a judged RAG eval JSON."""
from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "eval" / "results" / "rag_eval_judged_post_hybrid_20260508_223255.json"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    payload = json.loads(path.read_text(encoding="utf-8"))
    fails = []
    for x in payload["details"]:
        judge = x.get("judge") or {}

        def score(metric: str) -> int:
            return (judge.get(metric) or {}).get("score", 5)

        if (not x.get("recall_at_5")) or any(
            score(m) < 4
            for m in ["faithfulness", "citation_precision", "answer_completeness", "refusal_accuracy"]
        ):
            fails.append(x)

    print(f"failures: {len(fails)}")
    for f in fails:
        judge = f.get("judge") or {}
        evidence = f.get("evidence") or {}
        sql_block = evidence.get("sql") or {}
        print("-" * 80)
        print(f"id={f['id']} intent={f.get('intent')} difficulty={f.get('difficulty')}")
        print(f"recall@5={f.get('recall_at_5')} mrr={f.get('mrr')} template_id={sql_block.get('template_id')} sql_source={sql_block.get('sql_source')}")
        print(f"ambig={f.get('route', {}).get('ambiguity_type')} confidence={f.get('route', {}).get('confidence')}")
        print(f"Q: {f['question']}")
        print(f"expected: {f.get('expected_sources')}")
        print(f"actual:   {(f.get('actual_sources') or [])[:6]}")
        print(
            f"judge: faith={(judge.get('faithfulness') or {}).get('score')} "
            f"cite={(judge.get('citation_precision') or {}).get('score')} "
            f"comp={(judge.get('answer_completeness') or {}).get('score')} "
            f"ref={(judge.get('refusal_accuracy') or {}).get('score')}"
        )


if __name__ == "__main__":
    main()
