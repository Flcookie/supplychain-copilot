"""HITL approval: gated actions interrupt once; resume via Command. No LLM required."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from graph.approval import infer_proposed_action, needs_hitl, approval_node
from graph.state import SCState


def _sup012_state(**extra) -> dict:
    state = {
        "question": "Run a full supplier assessment for SUP012",
        "response_language": "en",
        "intent": "supplier_assessment",
        "supplier_id": "SUP012",
        "task_type": "supplier_assessment",
        "answer": "Recommend keeping Qualified with Reserve and reviewing country risk.",
        "assessment_profile": {
            "rows": [
                {
                    "supplier_id": "SUP012",
                    "qualification_status": "Qualified with Reserve",
                    "rating_class": "B",
                    "suggested_action": "Continue regular monitoring",
                    "risk_level": "Medium",
                }
            ]
        },
        "assessment_risk": {
            "rows": [
                {
                    "risk_event_id": "RSK0056",
                    "risk_type": "Geopolitical exposure",
                    "human_review_required": "Yes",
                    "recommended_action": "Monitor country risk",
                }
            ]
        },
    }
    state.update(extra)
    return state


def test_sup012_like_assessment_needs_hitl():
    proposed = infer_proposed_action(_sup012_state())
    assert proposed["gated"] is True
    assert proposed["writes_database"] is False
    assert proposed["action"] in {"status_change", "human_review"}
    assert any("Qualified with Reserve" in r for r in proposed["reasons"])
    assert any("human_review_required" in r for r in proposed["reasons"])
    assert needs_hitl(_sup012_state()) is True


def test_clean_qualified_supplier_skips_hitl():
    state = {
        "intent": "supplier_assessment",
        "answer": "Continue monitoring.",
        "human_approval_required": False,
        "assessment_profile": {
            "rows": [
                {
                    "qualification_status": "Qualified",
                    "rating_class": "A",
                    "suggested_action": "Continue regular monitoring",
                }
            ]
        },
        "assessment_risk": {
            "rows": [{"risk_event_id": "RSK1", "human_review_required": "No"}]
        },
    }
    assert infer_proposed_action(state)["gated"] is False
    assert needs_hitl(state) is False


def test_blacklist_question_is_gated():
    state = {
        "question": "Please blacklist SUP012 immediately",
        "answer": "I can only recommend a blacklist.",
        "intent": "risk_scenario",
        "scenario_spec": {"risk_type": "blacklist", "human_approval_required": True},
    }
    proposed = infer_proposed_action(state)
    assert proposed["gated"] is True
    assert proposed["action"] == "blacklist"


def test_clarification_skips_hitl():
    assert needs_hitl({"ambiguity_type": "missing_entity", "human_approval_required": True}) is False
    assert needs_hitl({"injection_blocked": True, "human_approval_required": True}) is False
    assert needs_hitl({"approval_decision": "approved", "human_approval_required": True}) is False


def test_approval_interrupt_then_resume_without_llm():
    def seed(state: SCState) -> SCState:
        return {"task_step": "seed"}

    def finish(state: SCState) -> SCState:
        return {"task_step": "done"}

    workflow = StateGraph(SCState)
    workflow.add_node("seed", seed)
    workflow.add_node("approval", approval_node)
    workflow.add_node("finish", finish)
    workflow.add_edge(START, "seed")
    workflow.add_edge("seed", "approval")
    workflow.add_edge("approval", "finish")
    workflow.add_edge("finish", END)
    app = workflow.compile(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "hitl-resume-1"}}

    paused = app.invoke(_sup012_state(thread_id="hitl-resume-1"), cfg)
    assert paused.get("__interrupt__")
    snap = app.get_state(cfg)
    assert "approval" in list(snap.next or [])
    payload = snap.interrupts[0].value if snap.interrupts else paused["__interrupt__"][0].value
    assert payload["kind"] == "human_approval"
    assert payload["writes_database"] is False
    assert payload["supplier_id"] == "SUP012"

    resumed = app.invoke(Command(resume={"approved": True, "note": "buyer ok"}), cfg)
    assert resumed.get("approval_decision") == "approved"
    assert resumed.get("task_step") == "done"
    assert "Human approval" in (resumed.get("answer") or "")
    assert app.get_state(cfg).next == ()


def test_reject_parks_recommendation():
    workflow = StateGraph(SCState)
    workflow.add_node("approval", approval_node)
    workflow.add_node("finish", lambda s: {"task_step": "done"})
    workflow.add_edge(START, "approval")
    workflow.add_edge("approval", "finish")
    workflow.add_edge("finish", END)
    app = workflow.compile(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "hitl-reject-1"}}
    app.invoke(_sup012_state(), cfg)
    resumed = app.invoke(Command(resume={"approved": False, "note": "hold"}), cfg)
    assert resumed.get("approval_decision") == "rejected"
    assert "Human rejection" in (resumed.get("answer") or "")


def test_full_graph_wires_approval_node():
    from graph.graph import build_graph

    graph = build_graph(use_checkpointer=False)
    node_names = set(graph.get_graph().nodes)
    assert "approval" in node_names
    assert "review" in node_names
    assert "evidence_boost" in node_names
    edges = {(str(u), str(v)) for u, v, *_ in graph.get_graph().edges}
    assert ("approval", "answer") in edges
    assert any(src == "review" for src, _ in edges)
