"""Smoke-test Ratti KPI SQL templates against ratti_copilot_demo.db."""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.kpi_sql_builder import build_kpi_sql
from tools.sql_tools import run_sql_query_with_meta

SQL_CASES = [
    ("EVAL010", "Show the on-time delivery rate and defect rate of yarn suppliers in 2025."),
    ("EVAL011", "Which suppliers had average delivery delay above 5 days?"),
    ("EVAL012", "Rank strategic suppliers by vendor rating score."),
    ("EVAL013", "Which suppliers have ESG score below 60 and missing certificates?"),
    ("EVAL014", "How much spend do we have by Kraljic quadrant?"),
    ("EVAL015", "Find suppliers whose certificate will expire in the next 60 days."),
    ("EVAL005", "What is the next step for supplier SUP008?"),
]


def main() -> None:
    results = []
    ok = 0
    for case_id, question in SQL_CASES:
        template = build_kpi_sql(question, {"metric": "other", "aggregation": "other"})
        entry = {"id": case_id, "question": question, "template_id": None, "ok": False}
        if template is None:
            entry["error"] = "no deterministic template matched"
            results.append(entry)
            continue
        entry["template_id"] = template.template_id
        try:
            result = run_sql_query_with_meta(template.sql, params=template.params)
            entry["row_count"] = result["meta"]["row_count"]
            entry["ok"] = result["meta"]["row_count"] >= 0
            ok += int(entry["ok"])
        except Exception as exc:
            entry["error"] = str(exc)
        results.append(entry)

    out_dir = os.path.join(ROOT, "eval", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ratti_sql_smoke.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"passed": ok, "total": len(SQL_CASES), "details": results}, f, indent=2)

    print(f"SQL smoke: {ok}/{len(SQL_CASES)} templates executed successfully")
    print(f"Report: {out_path}")
    for r in results:
        status = "OK" if r.get("ok") else "FAIL"
        print(f"  [{status}] {r['id']} template={r.get('template_id')} rows={r.get('row_count', 'n/a')}")


if __name__ == "__main__":
    main()
