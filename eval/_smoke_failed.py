"""Quick smoke run over the previously-failing samples to confirm convergence."""
from __future__ import annotations

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.graph import build_graph  # noqa: E402


SAMPLES = [
    "Which supplier has the most purchase orders?",
    "Compare suppliers in Vietnam by on-time delivery.",
    "Rank suppliers by delivery reliability.",
    "Which country has more delayed orders?",
    "Which materials are associated with late orders?",
    "What is OTIF for Alpha Electronics?",
    "Can you calculate defect rate from current demo data?",
    "Give me the risk score for Beta Plastics.",
    "Which supplier should be prioritized for a business review based on OTD and supplier policy?",
    "How should we handle a recurring late delivery issue under policy and KPI evidence?",
    "What does the supplier scorecard need to include and what current demo KPI can populate it?",
    "What data and policy evidence support classifying Gamma Metals as reliable?",
]


def main() -> None:
    g = build_graph()
    for q in SAMPLES:
        r = g.invoke({"question": q, "response_language": "en"})
        ev = r.get("evidence") or {}
        sql = ev.get("sql") or {}
        src_names = [s.get("source_name") for s in (ev.get("sources") or [])][:5]
        sql_source_marker = sql.get("sql_source")
        template_marker = sql.get("template_id")
        print(
            f"intent={r.get('intent')} amb={r.get('ambiguity_type')} "
            f"tpl={template_marker} sql_src={sql_source_marker} sources={src_names}"
        )
        print(f"   Q: {q}")
        print()


if __name__ == "__main__":
    main()
