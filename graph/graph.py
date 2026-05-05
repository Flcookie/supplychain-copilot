
from langgraph.graph import StateGraph, START, END

from .state import SCState
from .nodes import (
    answer_node,
    clarification_node,
    kpi_node,
    policy_qa_node,
    rag_fallback_node,
    router_node,
    scenario_node,
)


def build_graph():
    workflow = StateGraph(SCState)

    workflow.add_node("router", router_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("rag_fallback", rag_fallback_node)
    workflow.add_node("policy_qa", policy_qa_node)
    workflow.add_node("kpi", kpi_node)
    workflow.add_node("scenario", scenario_node)
    workflow.add_node("answer", answer_node)

    workflow.add_edge(START, "router")

    def route_decider(state: SCState):
        if state.get("baseline_mode"):
            intent = state.get("intent", "policy_qa")
            if intent == "kpi_query":
                return "kpi"
            if intent == "scenario_analysis":
                return "scenario"
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
        if intent == "scenario_analysis":
            return "scenario"
        return "policy_qa"

    workflow.add_conditional_edges(
        "router",
        route_decider,
        {
            "clarification": "clarification",
            "rag_fallback": "rag_fallback",
            "policy_qa": "policy_qa",
            "kpi": "kpi",
            "scenario": "scenario",
        },
    )

    workflow.add_edge("clarification", "answer")
    workflow.add_edge("rag_fallback", "answer")
    workflow.add_edge("policy_qa", "answer")
    workflow.add_edge("kpi", "answer")
    workflow.add_edge("scenario", "answer")
    workflow.add_edge("answer", END)

    return workflow.compile()
