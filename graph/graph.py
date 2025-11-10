
from langgraph.graph import StateGraph, START, END

from .state import SCState
from .nodes import router_node, policy_qa_node, kpi_node, scenario_node, answer_node


def build_graph():
    workflow = StateGraph(SCState)

    workflow.add_node("router", router_node)
    workflow.add_node("policy_qa", policy_qa_node)
    workflow.add_node("kpi", kpi_node)
    workflow.add_node("scenario", scenario_node)
    workflow.add_node("answer", answer_node)

    workflow.add_edge(START, "router")

    def route_decider(state: SCState):
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
            "policy_qa": "policy_qa",
            "kpi": "kpi",
            "scenario": "scenario",
        },
    )

    workflow.add_edge("policy_qa", "answer")
    workflow.add_edge("kpi", "answer")
    workflow.add_edge("scenario", "answer")
    workflow.add_edge("answer", END)

    return workflow.compile()
