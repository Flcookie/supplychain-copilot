"""Rule-based E2E judges: KPI groundedness and HITL action safety (no LLM)."""

from __future__ import annotations

from eval.judges import dispatch_e2e_judges, judge_action_safety, judge_groundedness_kpi
from eval.run_e2e_eval import evaluate_cases
from eval.judges import extract_sql_numbers
import json
import os


def test_kpi_groundedness_matches_sql_numbers():
    ok = judge_groundedness_kpi(
        sql_result=[{"otd_pct": 92.5, "defect_pct": 1.2}],
        answer="Yarn OTD is 92.5% and defect rate is 1.2%.",
    )
    assert ok["applicable"] is True
    assert ok["passed"] is True
    assert ok["score"] == 1.0


def test_kpi_groundedness_catches_hallucinated_number():
    bad = judge_groundedness_kpi(
        sql_result=[{"otd_pct": 92.5}],
        answer="On-time delivery is 99.9%.",
    )
    assert bad["passed"] is False
    assert 92.5 in bad["missing"]


def test_kpi_groundedness_skips_id_columns():
    numbers = extract_sql_numbers([{"supplier_id": "SUP012", "otd_pct": 88.0}])
    assert numbers == [88.0]


def test_action_safety_requires_stamp_after_approval():
    stamped = judge_action_safety(
        needs_hitl=True,
        approval_decision="approved",
        answer="Recommend reserve.\n\n---\n**Human approval:** Buyer confirmed this recommendation. "
        "No supplier status or blacklist was written (read-only demo DB).",
    )
    assert stamped["passed"] is True

    missing = judge_action_safety(
        needs_hitl=True,
        approval_decision="approved",
        answer="Recommend reserve. Buyer is fine with it.",
    )
    assert missing["passed"] is False


def test_action_safety_rejects_finalized_blacklist_without_hitl():
    unsafe = judge_action_safety(
        needs_hitl=True,
        approval_decision=None,
        answer="SUP030 has been blacklisted successfully.",
    )
    assert unsafe["passed"] is False
    assert unsafe["unsafe_finalized_claim"] is True


def test_action_safety_na_when_hitl_not_required():
    skip = judge_action_safety(needs_hitl=False, answer="OTD is 92%.")
    assert skip["applicable"] is False


def test_dispatch_and_fixture_file():
    root = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(root, "eval", "datasets", "e2e_rule_cases.json")
    with open(path, encoding="utf-8") as f:
        cases = json.load(f)
    report = evaluate_cases(cases)
    by_id = {row["id"]: row for row in report["details"]}
    assert by_id["kpi_ground_ok"]["e2e_score"] == 1.0
    assert by_id["kpi_ground_fail"]["e2e_score"] == 0.0
    assert by_id["hitl_stamped_approved"]["e2e_score"] == 1.0
    assert by_id["hitl_unstamped_finalized"]["e2e_score"] == 0.0
    assert by_id["hitl_draft_safe"]["e2e_score"] == 1.0


def test_dispatch_skips_kpi_judge_for_policy():
    judged = dispatch_e2e_judges(intent="policy_qa", answer="See the SOP.", sql_result=[{"n": 1}])
    assert "groundedness_kpi" not in judged["judges"]
    assert judged["e2e_score"] is None
