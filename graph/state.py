from typing import Annotated, List, Literal, Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class SCState(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], add_messages]

    question: str

    # Intent determined by the router
    intent: Literal["policy_qa", "kpi_query", "scenario_analysis", "unknown"]

    # RAG documents
    retrieved_docs: List[Dict[str, Any]]

    # (Reserved) KPI / SQL
    sql_query: Optional[str]
    sql_result: Optional[List[Dict[str, Any]]]

    # (Reserved) Scenario analysis
    scenario_spec: Optional[Dict[str, Any]]

    answer: Optional[str]
