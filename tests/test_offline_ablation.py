"""Offline ablation numbers must match frozen artifacts / live scanners."""

from __future__ import annotations

from eval.ablation import injection_ablation, rag_ablation, router_ablation


def test_rag_frozen_funnel_improves():
    rows = {row["stage"]: row for row in rag_ablation()}
    assert rows["vector-only"]["recall_at_5"] == 0.3333
    assert rows["hybrid-rrf"]["recall_at_5"] == 0.5667
    assert rows["hybrid-openai-rerank"]["recall_at_5"] == 0.8333
    assert rows["full-stack"]["recall_at_5"] == 1
    assert rows["full-stack"]["mrr"] == 0.9056
    assert rows["vector-only"]["recall_at_5"] < rows["hybrid-rrf"]["recall_at_5"]
    assert rows["hybrid-rrf"]["recall_at_5"] < rows["hybrid-openai-rerank"]["recall_at_5"]
    assert rows["hybrid-openai-rerank"]["recall_at_5"] <= rows["full-stack"]["recall_at_5"]


def test_router_offline_ladder():
    report = router_ablation()
    baseline = report["keyword_baseline"]["intent_accuracy"]
    heuristic = report["heuristic"]["intent_accuracy"]
    override = report["heuristic_plus_override"]["intent_accuracy"]
    archived_llm = report["llm_plus_override_archived"]["intent_accuracy"]
    assert baseline < heuristic
    assert heuristic <= override
    assert archived_llm >= 0.9
    assert override >= 0.64  # floor: override must beat the old "65%" narrative baseline


def test_injection_detector_is_perfect_on_eval_set():
    report = injection_ablation()
    assert report["samples"] == 30
    assert report["detector_accuracy"] == 1.0
