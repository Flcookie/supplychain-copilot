"""Structure + override tests for checkpoint, review, and assessment wiring."""

from __future__ import annotations

import os

import pytest

from core.router_overrides import apply_lifecycle_router_overrides


def test_assessment_override_with_supplier_id():
    parsed = {
        "intent": "policy_qa",
        "confidence": 0.5,
        "ambiguity_type": None,
        "human_approval_required": False,
        "reason": "x",
    }
    out = apply_lifecycle_router_overrides(
        parsed, "Run a full supplier assessment for SUP012."
    )
    assert out["intent"] == "supplier_assessment"
    assert out["ambiguity_type"] is None
    assert out["confidence"] >= 0.95


def test_assessment_override_missing_supplier():
    parsed = {
        "intent": "policy_qa",
        "confidence": 0.5,
        "ambiguity_type": None,
        "human_approval_required": False,
        "reason": "x",
    }
    out = apply_lifecycle_router_overrides(parsed, "请生成完整供应商评估报告")
    assert out["intent"] == "supplier_assessment"
    assert out["ambiguity_type"] == "missing_entity"


def test_review_evidence_gaps_rules():
    from graph.review import _evidence_gaps

    gaps = _evidence_gaps(
        {
            "intent": "policy_qa",
            "answer": "Policy requires ESG docs.",
            "retrieved_docs": [],
            "citations": [],
        }
    )
    assert "missing_policy_citations" in gaps

    gaps_ok = _evidence_gaps(
        {
            "intent": "policy_qa",
            "answer": "Policy requires ESG docs.",
            "retrieved_docs": [{"content": "ESG", "source": "policy.pdf"}],
            "citations": [{"type": "document", "source": "policy.pdf"}],
        }
    )
    assert gaps_ok == []


def test_graph_contains_review_and_assessment_nodes():
    from graph.graph import build_graph

    graph = build_graph(use_checkpointer=False)
    node_names = set(graph.get_graph().nodes)
    for name in (
        "review",
        "evidence_boost",
        "assessment_dispatch",
        "assessment_gather",
        "assessment_profile",
        "assessment_kpi",
        "assessment_policy",
        "assessment_risk",
        "assessment_synthesize",
    ):
        assert name in node_names


def test_review_and_assessment_edges():
    from graph.graph import build_graph

    graph = build_graph(use_checkpointer=False)
    edges = {(str(u), str(v)) for u, v, *_ in graph.get_graph().edges}
    assert ("policy_qa", "review") in edges
    assert ("kpi", "review") in edges
    assert ("hybrid_aggregate", "review") in edges
    assert ("assessment_synthesize", "review") in edges
    assert ("assessment_gather", "assessment_profile") in edges
    assert ("assessment_gather", "assessment_kpi") in edges
    assert ("review", "answer") in edges or any(
        e[0] == "review" for e in edges
    )


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="graph.invoke on this path calls the LLM router",
)
def test_checkpoint_persists_thread_state():
    from langgraph.checkpoint.memory import MemorySaver

    from graph.graph import build_graph

    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-thread-assessment-1"}}
    # Clarification-only path should checkpoint without needing external tools much.
    result = graph.invoke(
        {
            "question": "Compare they",
            "response_language": "en",
            "intent": "kpi_query",
            "confidence": 0.4,
            "ambiguity_type": "coreference",
            "baseline_mode": False,
            "review_attempts": 0,
            "thread_id": "test-thread-assessment-1",
        },
        config,
    )
    # Router may override; either clarification or some answer should exist.
    assert result.get("answer")
    snap = graph.get_state(config)
    assert snap.values.get("question")
    history = list(graph.get_state_history(config))
    assert len(history) >= 1
