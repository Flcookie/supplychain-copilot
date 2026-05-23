"""Generate REGRESSION.md entries from a judged RAG eval JSON.

A failure is any sample where ANY of the following is true:
- recall_at_5 is False
- judge.faithfulness.score < 4
- judge.citation_precision.score < 4
- judge.answer_completeness.score < 4
- judge.refusal_accuracy.score < 4

Each failure becomes a structured Markdown block with a heuristic root-cause
classification so a human can later own and resolve it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT = os.path.join(ROOT_DIR, "eval", "REGRESSION.md")


def _classify_failure(detail: dict) -> tuple[list[str], str]:
    failures: list[str] = []
    judge = detail.get("judge") or {}
    faith = (judge.get("faithfulness") or {}).get("score")
    citation = (judge.get("citation_precision") or {}).get("score")
    completeness = (judge.get("answer_completeness") or {}).get("score")
    refusal = (judge.get("refusal_accuracy") or {}).get("score")

    if not detail.get("recall_at_5", True):
        failures.append("retrieval")
    if faith is not None and faith < 4:
        failures.append("faithfulness")
    if citation is not None and citation < 4:
        failures.append("citation")
    if completeness is not None and completeness < 4:
        failures.append("completeness")
    if refusal is not None and refusal < 4:
        failures.append("refusal")

    route = detail.get("route") or {}
    if route.get("ambiguity_type"):
        failures.append("routing")

    if not failures:
        return [], "n/a"

    if "retrieval" in failures:
        root_cause = "retrieved_sources missed expected document; need chunker / hybrid weighting tweak"
    elif "routing" in failures:
        root_cause = f"router emitted ambiguity_type={route.get('ambiguity_type')}; expected null"
    elif "refusal" in failures:
        root_cause = "answer refused (or accepted) when answerability dictates the opposite"
    elif "completeness" in failures:
        root_cause = "expected answer points missing from response"
    elif "faithfulness" in failures:
        root_cause = "claim not fully supported by retrieved evidence"
    elif "citation" in failures:
        root_cause = "citations did not directly support the answer"
    else:
        root_cause = "needs investigation"
    return failures, root_cause


def render(report_path: str) -> str:
    with open(report_path, encoding="utf-8") as f:
        payload = json.load(f)

    eval_run = os.path.basename(report_path)
    details = payload.get("details", [])

    open_failures = []
    for detail in details:
        failure_types, root_cause = _classify_failure(detail)
        if not failure_types:
            continue
        judge = detail.get("judge") or {}
        block = [
            f"### Sample `{detail.get('id')}` — {detail.get('intent')} / {detail.get('difficulty')}",
            "",
            f"- Eval run: `{eval_run}`",
            f"- Question: {detail.get('question')}",
            f"- Expected sources: {', '.join(detail.get('expected_sources') or []) or 'n/a'}",
            f"- Actual sources (top): {', '.join((detail.get('actual_sources') or [])[:5]) or 'none'}",
            f"- Recall@5: {detail.get('recall_at_5')}  ·  MRR: {detail.get('mrr')}",
            f"- Judge scores: faithfulness={(judge.get('faithfulness') or {}).get('score')}, citation_precision={(judge.get('citation_precision') or {}).get('score')}, answer_completeness={(judge.get('answer_completeness') or {}).get('score')}, refusal_accuracy={(judge.get('refusal_accuracy') or {}).get('score')}",
            f"- Failure types: {', '.join(failure_types)}",
            f"- Root cause hypothesis: {root_cause}",
            "- Fix:",
            "- Owner:",
            "- Status: open",
            "",
        ]
        open_failures.append("\n".join(block))

    header = [
        "# Regression Failure Log",
        "",
        "Use this file to preserve failed evaluation cases and follow-up fixes.",
        "",
        "## Template",
        "",
        "- Eval run:",
        "- Sample id:",
        "- Question:",
        "- Expected behavior:",
        "- Actual behavior:",
        "- Failure type: retrieval | citation | faithfulness | completeness | refusal | routing | latency",
        "- Root cause:",
        "- Fix:",
        "- Owner:",
        "- Status:",
        "",
        f"_Last refreshed from `{eval_run}` on {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}._",
        "",
        "## Open Failures",
        "",
    ]
    if not open_failures:
        return "\n".join(header) + "No failures detected in latest run.\n"
    return "\n".join(header) + "\n".join(open_failures)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, help="Path to judged rag_eval_*.json")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not os.path.exists(args.report):
        print(f"Report not found: {args.report}", file=sys.stderr)
        sys.exit(1)

    rendered = render(args.report)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(f"Regression log written to {args.output}")


if __name__ == "__main__":
    main()
