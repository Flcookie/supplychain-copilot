import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from core.config import LLM_MODEL
from core.prompts import (
    KPI_ANSWER_PROMPT,
    KPI_SQL_PROMPT,
    POLICY_QA_PROMPT,
    RAG_FALLBACK_PROMPT,
    ROUTER_PROMPT,
    SCENARIO_ANALYSIS_PROMPT,
)
from rag.retriever import get_retriever
from tools.sql_tools import run_sql_query_with_meta
from .state import SCState

llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
retriever = get_retriever()


def _safe_json_load(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def _build_clarification_question(ambiguity_type: str | None) -> str:
    if ambiguity_type == "coreference":
        return "When you say 'they/this supplier', which supplier are you referring to?"
    if ambiguity_type == "composite_intent":
        return "Do you want policy standards first, or supplier KPI data first?"
    if ambiguity_type == "missing_entity":
        return "Please specify supplier name and time range (for example: Alpha, last 3 months)."
    return "Could you clarify your request so I can answer precisely?"


def _build_doc_citations(docs: list) -> list:
    citations = []
    for i, doc in enumerate(docs, start=1):
        citations.append(
            {
                "type": "document",
                "source": doc.metadata.get("source", ""),
                "chunk_id": f"doc-{i}",
                "clause": doc.metadata.get("section", ""),
            }
        )
    return citations


def router_node(state: SCState) -> SCState:
    q = state["question"]
    prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT)
    resp = llm.invoke(prompt.format(question=q))

    parsed = {
        "intent": "policy_qa",
        "confidence": 0.6,
        "ambiguity_type": None,
        "reason": "router defaulted due to unparsable output",
    }
    try:
        llm_result = _safe_json_load(resp.content.strip())
        parsed["intent"] = llm_result.get("intent", parsed["intent"])
        parsed["confidence"] = float(llm_result.get("confidence", parsed["confidence"]))
        parsed["ambiguity_type"] = llm_result.get("ambiguity_type")
        parsed["reason"] = llm_result.get("reason", parsed["reason"])
    except Exception:
        pass

    if parsed["intent"] not in ["policy_qa", "kpi_query", "scenario_analysis"]:
        parsed["intent"] = "policy_qa"

    state["intent"] = parsed["intent"]
    state["confidence"] = max(0.0, min(parsed["confidence"], 1.0))
    state["ambiguity_type"] = parsed["ambiguity_type"]
    state["reason"] = parsed["reason"]
    state["fallback_mode"] = "none"
    state["route_decision"] = {
        "intent": state["intent"],
        "confidence": state["confidence"],
        "ambiguity_type": state["ambiguity_type"],
        "reason": state["reason"],
    }
    return state


def clarification_node(state: SCState) -> SCState:
    clarification = _build_clarification_question(state.get("ambiguity_type"))
    state["clarification_question"] = clarification
    state["answer"] = (
        f"I need one clarification before routing this request.\n\n{clarification}\n\n"
        "Reply with the missing details and I will continue."
    )
    return state


def rag_fallback_node(state: SCState) -> SCState:
    q = state["question"]
    docs = retriever.invoke(q)
    state["retrieved_docs"] = [{"content": d.page_content, "source": d.metadata.get("source", "")} for d in docs]
    state["citations"] = _build_doc_citations(docs)
    context = "\n\n".join(d.page_content for d in docs)
    prompt = ChatPromptTemplate.from_template(RAG_FALLBACK_PROMPT)
    resp = llm.invoke(prompt.format(question=q, context=context))
    state["fallback_mode"] = "rag_fallback"
    state["answer"] = resp.content
    return state


def policy_qa_node(state: SCState) -> SCState:
    q = state["question"]
    docs = retriever.invoke(q)
    state["retrieved_docs"] = [{"content": d.page_content, "source": d.metadata.get("source", "")} for d in docs]
    state["citations"] = _build_doc_citations(docs)
    context = "\n\n".join(d.page_content for d in docs)
    prompt = ChatPromptTemplate.from_template(POLICY_QA_PROMPT)
    resp = llm.invoke(prompt.format(question=q, context=context))
    state["answer"] = resp.content
    return state


def kpi_node(state: SCState) -> SCState:
    q = state["question"]
    prompt = ChatPromptTemplate.from_template(KPI_SQL_PROMPT)
    sql = llm.invoke(prompt.format(question=q)).content.strip()
    state["sql_query"] = sql

    try:
        result = run_sql_query_with_meta(sql)
        rows = result["rows"]
        sql_meta = result["meta"]
    except Exception as e:
        state["answer"] = f"Error while running KPI query: {e}"
        state["sql_result"] = []
        state["sql_meta"] = {"row_count": 0, "latency_ms": None, "error": str(e)}
        state["citations"] = [{"type": "sql", "sql": sql, "row_count": 0, "latency_ms": None, "error": str(e)}]
        return state

    state["sql_result"] = rows
    state["sql_meta"] = sql_meta
    state["citations"] = [
        {
            "type": "sql",
            "sql": sql,
            "row_count": sql_meta.get("row_count", 0),
            "latency_ms": sql_meta.get("latency_ms"),
        }
    ]

    explain_prompt = ChatPromptTemplate.from_template(KPI_ANSWER_PROMPT)
    resp = llm.invoke(explain_prompt.format(question=q, sql=sql, rows=json.dumps(rows, ensure_ascii=False)))
    state["answer"] = resp.content
    return state


def scenario_node(state: SCState) -> SCState:
    q = state["question"]
    parse_prompt = ChatPromptTemplate.from_template(
        """
        Extract supply chain risk scenario parameters from the following question (in Chinese or English) and return as JSON:
        Fields:
        - country: Country of affected suppliers (e.g., 'VN', 'CN', 'DE'); if not mentioned, use null
        - delay_days: Expected general delay days (integer); if not mentioned, use 7 as default
        Output only JSON, no explanations.
        Question:
        {question}
        """
    )
    parsed_raw = llm.invoke(parse_prompt.format(question=q)).content.strip()
    try:
        scenario_spec = _safe_json_load(parsed_raw)
    except Exception:
        scenario_spec = {"country": None, "delay_days": 7}

    state["scenario_spec"] = scenario_spec
    country = scenario_spec.get("country") or "VN"
    sql = """
    SELECT s.name AS supplier_name,
           s.country,
           COUNT(p.id) AS total_pos,
           SUM(p.qty) AS total_qty
    FROM suppliers s
    JOIN purchase_orders p ON s.id = p.supplier_id
    WHERE s.country = ?
    GROUP BY s.id;
    """
    try:
        result = run_sql_query_with_meta(sql, params=(country,))
        impact_rows = result["rows"]
        state["sql_query"] = f"{sql.strip()} -- params: ({country},)"
        state["sql_result"] = impact_rows
        state["sql_meta"] = result["meta"]
        state["citations"] = [
            {
                "type": "sql",
                "sql": sql.strip(),
                "params": {"country": country},
                "row_count": result["meta"].get("row_count", 0),
                "latency_ms": result["meta"].get("latency_ms"),
            }
        ]
    except Exception as e:
        impact_rows = [{"error": str(e)}]
        state["citations"] = [{"type": "sql", "sql": sql.strip(), "error": str(e)}]

    explain_prompt = ChatPromptTemplate.from_template(SCENARIO_ANALYSIS_PROMPT)
    resp = llm.invoke(
        explain_prompt.format(
            question=q,
            scenario_spec=json.dumps(scenario_spec, ensure_ascii=False),
            impact_rows=json.dumps(impact_rows, ensure_ascii=False),
        )
    )
    state["answer"] = resp.content
    return state


def answer_node(state: SCState) -> SCState:
    if "citations" not in state:
        state["citations"] = []
    return state
