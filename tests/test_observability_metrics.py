"""Observability metrics + badcase export over an isolated traces DB."""

from __future__ import annotations

from observability.metrics import summarize_metrics
from observability.store import TraceStore
from eval.badcase_export import select_badcases


def test_metrics_aggregate_router_hitl_latency(tmp_path):
    store = TraceStore(db_path=str(tmp_path / "traces.db"))
    store.create_trace("t1", "Why is SUP012 rated C?", "en")
    store.add_step("t1", 1, "llm", prompt_tokens=10, completion_tokens=20)
    store.finish_trace(
        "t1",
        final_answer="C rating because OTD is 88.0.",
        confidence=0.94,
        intent="vendor_rating_explanation",
        total_latency_ms=1200,
        ambiguity_type=None,
        review_status="passed",
        human_approval_required=False,
    )

    store.create_trace("t2", "they?", "en")
    store.finish_trace(
        "t2",
        final_answer="Which supplier?",
        confidence=0.55,
        intent="kpi_query",
        total_latency_ms=400,
        ambiguity_type="coreference",
        review_status="skipped",
        human_approval_required=False,
    )

    store.create_trace("t3", "Blacklist SUP030", "en")
    store.finish_trace(
        "t3",
        final_answer="Paused.",
        confidence=0.93,
        intent="risk_scenario",
        total_latency_ms=800,
        review_status="needs_more_evidence",
        human_approval_required=True,
    )

    store.create_trace("t4", "boom", "en")
    store.finish_trace("t4", error="pinecone timeout", total_latency_ms=50)

    metrics = summarize_metrics(store, hours=None)
    assert metrics["traces"] == 4
    assert metrics["clarification_rate"] == 0.25
    assert metrics["hitl_trigger_rate"] == 0.25
    assert metrics["review_evidence_boost_rate"] == 0.25
    assert metrics["low_confidence_rate"] == 0.25
    assert metrics["error_rate"] == 0.25
    assert metrics["p50_latency_ms"] is not None
    assert metrics["p95_latency_ms"] is not None
    intents = {row["intent"]: row["count"] for row in metrics["router_intent_distribution"]}
    assert intents["vendor_rating_explanation"] == 1
    assert metrics["total_prompt_tokens"] == 10
    assert metrics["total_completion_tokens"] == 20


def test_badcase_export_selects_low_confidence_and_errors(tmp_path):
    store = TraceStore(db_path=str(tmp_path / "traces.db"))
    store.create_trace("ok", "How is ESG calculated?", "en")
    store.finish_trace("ok", confidence=0.96, intent="policy_qa")
    store.create_trace("low", "hmm?", "en")
    store.finish_trace("low", confidence=0.4, intent="policy_qa")
    store.create_trace("err", "fail", "en")
    store.finish_trace("err", error="timeout", confidence=0.9, intent="kpi_query")
    store.create_trace("resume", "resume:abc", "en")
    store.finish_trace("resume", confidence=0.2, intent="supplier_assessment")

    cases = select_badcases(store.list_traces(limit=20), limit=10)
    questions = {c["question"] for c in cases}
    assert "hmm?" in questions
    assert "fail" in questions
    assert "How is ESG calculated?" not in questions
    assert "resume:abc" not in questions
