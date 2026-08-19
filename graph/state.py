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
        "supplier_assessment",
        "unknown",
    ]
    confidence: float
    reason: str
    ambiguity_type: Optional[
        Literal["coreference", "composite_intent", "missing_entity", "overbroad_data_request"]
    ]
    human_approval_required: Optional[bool]
    proposed_action: Optional[str]
    proposed_action_reasons: Optional[List[str]]
    approval_decision: Optional[Literal["approved", "rejected"]]
    approval_note: Optional[str]
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

    # Prompt-injection / security
    injection_scan: Optional[Dict[str, Any]]
    injection_blocked: Optional[bool]

    # Parallel hybrid branches (policy ∥ kpi → aggregate)
    policy_partial_answer: Optional[str]
    kpi_partial_answer: Optional[str]
    hybrid_parallel: Optional[bool]
    hybrid_policy_docs: Optional[List[Dict[str, Any]]]
    hybrid_sql_evidence: Optional[Dict[str, Any]]
    hybrid_sample_size: Optional[int]
    hybrid_minimum_sample_size: Optional[int]
    cache_hit: Optional[bool]

    # Checkpoint / task identity
    thread_id: Optional[str]
    task_type: Optional[Literal["chat", "supplier_assessment"]]
    supplier_id: Optional[str]

    # Review Agent
    review_status: Optional[
        Literal["pending", "passed", "failed", "needs_more_evidence", "skipped"]
    ]
    review_notes: Optional[str]
    review_attempts: Optional[int]
    unsupported_claims: Optional[List[str]]

    # Supplier assessment task (parallel gather → synthesize)
    task_plan: Optional[List[str]]
    task_step: Optional[str]
    assessment_profile: Optional[Dict[str, Any]]
    assessment_kpi: Optional[Dict[str, Any]]
    assessment_policy_docs: Optional[List[Dict[str, Any]]]
    assessment_risk: Optional[Dict[str, Any]]
    assessment_orders: Optional[Dict[str, Any]]
