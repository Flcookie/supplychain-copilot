from typing import Annotated, List, Literal, Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from core.evidence import Evidence


class SCState(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], add_messages]

    question: str
    response_language: Optional[Literal["en", "zh"]]

    # Intent determined by the router
    intent: Literal[
        "policy_qa",
        "kpi_query",
        "risk_scenario",
        "scenario_analysis",
        "hybrid_query",
        "qualification_checklist",
        "vendor_rating_explanation",
        "unknown",
    ]
    confidence: float
    reason: str
    ambiguity_type: Optional[
        Literal["coreference", "composite_intent", "missing_entity", "overbroad_data_request"]
    ]
    human_approval_required: Optional[bool]
    clarification_question: Optional[str]
    fallback_mode: Optional[Literal["none", "rag_fallback"]]
    baseline_mode: Optional[bool]

    # RAG documents
    retrieved_docs: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    evidence: Optional[Evidence]

    # (Reserved) KPI / SQL
    kpi_parse: Optional[Dict[str, Any]]
    sql_query: Optional[str]
    sql_result: Optional[List[Dict[str, Any]]]
    sql_meta: Optional[Dict[str, Any]]

    # (Reserved) Scenario analysis
    scenario_spec: Optional[Dict[str, Any]]

    route_decision: Optional[Dict[str, Any]]
    answer: Optional[str]
