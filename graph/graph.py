
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .assessment import (
    assessment_dispatch_node,
    assessment_kpi_branch,
    assessment_orders_branch,
    assessment_policy_branch,
    assessment_profile_branch,
    assessment_risk_branch,
    assessment_synthesize_node,
)
from .checkpoint import get_checkpointer
from .nodes import (
    answer_node,
    clarification_node,
    hybrid_aggregate_node,
    hybrid_dispatch_node,
    hybrid_kpi_branch,
    hybrid_policy_branch,
    kpi_node,
    policy_qa_node,
    qualification_checklist_node,
    rag_fallback_node,
    router_node,
    scenario_node,
    vendor_rating_node,
)
from .approval import approval_node, needs_hitl
from .review import evidence_boost_node, review_node
from .state import SCState


def _assessment_gather_gate(state: SCState) -> SCState:
    """Passthrough fan-out hub after dispatch confirms a supplier id."""
    return {"task_step": "gather"}


def build_graph(*, checkpointer=None, use_checkpointer: bool = True):
    """Compile the Supplier Copilot StateGraph.

    Args:
        checkpointer: optional explicit saver (tests may pass MemorySaver()).
        use_checkpointer: when False, compile without persistence (unit structure tests).
    """
    workflow = StateGraph(SCState)

    workflow.add_node("router", router_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("rag_fallback", rag_fallback_node)
    workflow.add_node("policy_qa", policy_qa_node)
    workflow.add_node("kpi", kpi_node)
    workflow.add_node("hybrid_dispatch", hybrid_dispatch_node)
    workflow.add_node("hybrid_policy", hybrid_policy_branch)
    workflow.add_node("hybrid_kpi", hybrid_kpi_branch)
    workflow.add_node("hybrid_aggregate", hybrid_aggregate_node)
    workflow.add_node("scenario", scenario_node)
    workflow.add_node("qualification_checklist", qualification_checklist_node)
    workflow.add_node("vendor_rating", vendor_rating_node)

    workflow.add_node("assessment_dispatch", assessment_dispatch_node)
    workflow.add_node("assessment_gather", _assessment_gather_gate)
    workflow.add_node("assessment_profile", assessment_profile_branch)
    workflow.add_node("assessment_orders", assessment_orders_branch)
    workflow.add_node("assessment_kpi", assessment_kpi_branch)
    workflow.add_node("assessment_policy", assessment_policy_branch)
    workflow.add_node("assessment_risk", assessment_risk_branch)
    workflow.add_node("assessment_synthesize", assessment_synthesize_node)

    workflow.add_node("review", review_node)
    workflow.add_node("evidence_boost", evidence_boost_node)
    workflow.add_node("approval", approval_node)
    workflow.add_node("answer", answer_node)

    workflow.add_edge(START, "router")

    def route_decider(state: SCState):
        if state.get("baseline_mode"):
            intent = state.get("intent", "policy_qa")
            if intent == "kpi_query":
                return "kpi"
            if intent in {"scenario_analysis", "risk_scenario"}:
                return "scenario"
            if intent == "hybrid_query":
                return "hybrid_dispatch"
            if intent == "qualification_checklist":
                return "qualification_checklist"
            if intent == "vendor_rating_explanation":
                return "vendor_rating"
            if intent == "supplier_assessment":
                return "assessment_dispatch"
            return "policy_qa"
        if state.get("ambiguity_type"):
            return "clarification"
        if state.get("confidence", 0.0) < 0.75:
            return "rag_fallback"
        intent = state.get("intent", "policy_qa")
        if intent == "policy_qa":
            return "policy_qa"
        if intent == "kpi_query":
            return "kpi"
        if intent in {"scenario_analysis", "risk_scenario"}:
            return "scenario"
        if intent == "hybrid_query":
            return "hybrid_dispatch"
        if intent == "qualification_checklist":
            return "qualification_checklist"
        if intent == "vendor_rating_explanation":
            return "vendor_rating"
        if intent == "supplier_assessment":
            return "assessment_dispatch"
        return "policy_qa"

    workflow.add_conditional_edges(
        "router",
        route_decider,
        {
            "clarification": "clarification",
            "rag_fallback": "rag_fallback",
            "policy_qa": "policy_qa",
            "kpi": "kpi",
            "hybrid_dispatch": "hybrid_dispatch",
            "scenario": "scenario",
            "qualification_checklist": "qualification_checklist",
            "vendor_rating": "vendor_rating",
            "assessment_dispatch": "assessment_dispatch",
        },
    )

    # Hybrid fan-out / join
    workflow.add_edge("hybrid_dispatch", "hybrid_policy")
    workflow.add_edge("hybrid_dispatch", "hybrid_kpi")
    workflow.add_edge("hybrid_policy", "hybrid_aggregate")
    workflow.add_edge("hybrid_kpi", "hybrid_aggregate")
    workflow.add_edge("hybrid_aggregate", "review")

    # Assessment: dispatch → (clarify path | gather fan-out) → synthesize → review
    def assessment_decider(state: SCState):
        if state.get("ambiguity_type"):
            return "review"
        return "assessment_gather"

    workflow.add_conditional_edges(
        "assessment_dispatch",
        assessment_decider,
        {
            "review": "review",
            "assessment_gather": "assessment_gather",
        },
    )
    workflow.add_edge("assessment_gather", "assessment_profile")
    workflow.add_edge("assessment_gather", "assessment_orders")
    workflow.add_edge("assessment_gather", "assessment_kpi")
    workflow.add_edge("assessment_gather", "assessment_policy")
    workflow.add_edge("assessment_gather", "assessment_risk")
    for node in (
        "assessment_profile",
        "assessment_orders",
        "assessment_kpi",
        "assessment_policy",
        "assessment_risk",
    ):
        workflow.add_edge(node, "assessment_synthesize")
    workflow.add_edge("assessment_synthesize", "review")

    # Specialists → Review → (optional evidence boost) → Answer
    workflow.add_edge("clarification", "review")
    workflow.add_edge("rag_fallback", "review")
    workflow.add_edge("policy_qa", "review")
    workflow.add_edge("kpi", "review")
    workflow.add_edge("scenario", "review")
    workflow.add_edge("qualification_checklist", "review")
    workflow.add_edge("vendor_rating", "review")

    def after_review(state: SCState):
        if state.get("review_status") == "needs_more_evidence":
            return "evidence_boost"
        if needs_hitl(state):
            return "approval"
        return "answer"

    workflow.add_conditional_edges(
        "review",
        after_review,
        {
            "evidence_boost": "evidence_boost",
            "approval": "approval",
            "answer": "answer",
        },
    )
    workflow.add_edge("evidence_boost", "review")
    workflow.add_edge("approval", "answer")
    workflow.add_edge("answer", END)

    if not use_checkpointer:
        return workflow.compile()

    saver = checkpointer if checkpointer is not None else get_checkpointer()
    return workflow.compile(checkpointer=saver)


def build_graph_for_tests():
    """Ephemeral in-memory checkpointer for pytest."""
    return build_graph(checkpointer=MemorySaver(), use_checkpointer=True)
