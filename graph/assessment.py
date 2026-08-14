"""Supplier assessment task: parallel profile / KPI / policy / risk → synthesis."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from core.demo_constants import RATTI_DATA_SNAPSHOT
from core.evidence import hybrid_evidence
from core.llm import get_llm
from core.prompts import SUPPLIER_ASSESSMENT_PROMPT
from rag.retriever import get_retriever
from tools.sql_tools import run_sql_query_with_meta

from .state import SCState


def _zh(state: SCState) -> bool:
    return state.get("response_language", "en") == "zh"


def _supplier_id(state: SCState) -> str | None:
    sid = state.get("supplier_id")
    if sid:
        return str(sid).upper()
    import re

    match = re.search(r"(SUP\d{3})", state.get("question") or "", re.IGNORECASE)
    return match.group(1).upper() if match else None


def assessment_dispatch_node(state: SCState) -> SCState:
    sid = _supplier_id(state)
    if not sid:
        is_zh = _zh(state)
        state["ambiguity_type"] = "missing_entity"
        state["clarification_question"] = (
            "请提供供应商编号（例如 SUP012），以便生成完整评估报告。"
            if is_zh
            else "Please provide a supplier ID (e.g. SUP012) to run a full assessment."
        )
        state["answer"] = (
            f"在生成供应商评估前需要确认实体。\n\n{state['clarification_question']}"
            if is_zh
            else f"I need a supplier entity before running the assessment.\n\n{state['clarification_question']}"
        )
        state["task_step"] = "awaiting_supplier_id"
        return state

    state["supplier_id"] = sid
    state["task_type"] = "supplier_assessment"
    state["intent"] = "supplier_assessment"
    state["task_plan"] = [
        "profile",
        "orders",
        "kpi",
        "policy",
        "risk",
        "synthesize",
        "review",
    ]
    state["task_step"] = "dispatch"
    return state


def assessment_profile_branch(state: SCState) -> SCState:
    """Archive snapshot: supplier master + qualification + rating."""
    if state.get("ambiguity_type"):
        return {}
    sid = state.get("supplier_id") or _supplier_id(state)
    sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       s.category_level_2,
       s.country,
       s.kraljic_quadrant,
       s.qualification_status,
       s.risk_level,
       s.supply_risk_score,
       s.single_sourcing_flag,
       s.next_review_date,
       vr.rating_class,
       vr.final_vendor_rating_score,
       vr.suggested_action
FROM suppliers s
LEFT JOIN vendor_rating vr ON s.supplier_id = vr.supplier_id
WHERE s.supplier_id = ?
ORDER BY vr.period DESC
LIMIT 1
"""
    meta = run_sql_query_with_meta(sql, params=(sid,))
    return {
        "assessment_profile": {
            "sql": sql.strip(),
            "rows": meta.get("rows") or [],
            "latency_ms": meta.get("latency_ms"),
        }
    }


def assessment_orders_branch(state: SCState) -> SCState:
    if state.get("ambiguity_type"):
        return {}
    sid = state.get("supplier_id") or _supplier_id(state)
    sql = """
SELECT COUNT(*) AS po_count,
       ROUND(SUM(order_amount_eur), 2) AS total_spend_eur,
       MIN(order_date) AS first_order,
       MAX(order_date) AS last_order
FROM purchase_orders
WHERE supplier_id = ?
"""
    meta = run_sql_query_with_meta(sql, params=(sid,))
    return {
        "assessment_orders": {
            "sql": sql.strip(),
            "rows": meta.get("rows") or [],
            "latency_ms": meta.get("latency_ms"),
        }
    }

def assessment_kpi_branch(state: SCState) -> SCState:
    if state.get("ambiguity_type"):
        return {}
    sid = state.get("supplier_id") or _supplier_id(state)
    sql = """
SELECT
  (SELECT ROUND(AVG(on_time_flag) * 100, 2) FROM delivery_events WHERE supplier_id = ?) AS otd_pct,
  (SELECT ROUND(AVG(delivery_delay_days), 2) FROM delivery_events WHERE supplier_id = ?) AS avg_delay_days,
  (SELECT ROUND(AVG(defect_rate) * 100, 2) FROM quality_events WHERE supplier_id = ?) AS avg_defect_pct,
  (SELECT COUNT(*) FROM quality_events WHERE supplier_id = ?) AS quality_event_count,
  (SELECT COUNT(*) FROM delivery_events WHERE supplier_id = ?) AS delivery_event_count
"""
    meta = run_sql_query_with_meta(sql, params=(sid, sid, sid, sid, sid))
    # Parallel-safe: only write branch-private keys (no shared sql_*/retrieved_docs).
    return {
        "assessment_kpi": {
            "sql": sql.strip(),
            "rows": meta.get("rows") or [],
            "latency_ms": meta.get("latency_ms"),
        }
    }


def assessment_policy_branch(state: SCState) -> SCState:
    if state.get("ambiguity_type"):
        return {}
    sid = state.get("supplier_id") or ""
    # Do not depend on sibling parallel branch outputs.
    query = (
        f"supplier monitoring qualification ESG vendor rating and risk policy "
        f"applicable to supplier {sid}"
    )
    docs = get_retriever(k=5, doc_types=["policy", "contract", "sop", "faq"]).invoke(query)
    return {
        "assessment_policy_docs": [
            {
                "content": d.page_content,
                "source": d.metadata.get("source_name") or d.metadata.get("source", ""),
                "chunk_id": d.metadata.get("chunk_id"),
                "doc_type": d.metadata.get("doc_type"),
            }
            for d in docs
        ]
    }


def assessment_risk_branch(state: SCState) -> SCState:
    if state.get("ambiguity_type"):
        return {}
    sid = state.get("supplier_id") or _supplier_id(state)
    sql = """
SELECT risk_event_id,
       risk_type,
       risk_score_1_25,
       recommended_action,
       human_review_required,
       event_date
FROM risk_events
WHERE supplier_id = ?
ORDER BY risk_score_1_25 DESC, event_date DESC
LIMIT 10
"""
    meta = run_sql_query_with_meta(sql, params=(sid,))
    quality_sql = """
SELECT quality_event_id, event_date, non_conformity_type, severity, defect_rate
FROM quality_events
WHERE supplier_id = ?
ORDER BY event_date DESC
LIMIT 5
"""
    try:
        qmeta = run_sql_query_with_meta(quality_sql, params=(sid,))
        quality_rows = qmeta.get("rows") or []
    except Exception:
        quality_rows = []
    return {
        "assessment_risk": {
            "sql": sql.strip(),
            "rows": meta.get("rows") or [],
            "quality_rows": quality_rows,
            "latency_ms": meta.get("latency_ms"),
        }
    }


def assessment_synthesize_node(state: SCState) -> SCState:
    if state.get("ambiguity_type"):
        return state

    sid = state.get("supplier_id") or _supplier_id(state)
    profile = state.get("assessment_profile") or {}
    orders = state.get("assessment_orders") or {}
    kpi = state.get("assessment_kpi") or {}
    risk = state.get("assessment_risk") or {}
    policy_docs = state.get("assessment_policy_docs") or []

    citations: list[dict[str, Any]] = []
    for label, block in (
        ("profile", profile),
        ("orders", orders),
        ("kpi", kpi),
        ("risk", risk),
    ):
        if block.get("sql"):
            citations.append(
                {
                    "type": "sql",
                    "label": label,
                    "sql": block["sql"],
                    "row_count": len(block.get("rows") or []),
                }
            )
    for i, doc in enumerate(policy_docs, start=1):
        citations.append(
            {
                "type": "document",
                "source": doc.get("source", ""),
                "chunk_id": doc.get("chunk_id") or f"assess-doc-{i}",
                "doc_type": doc.get("doc_type", ""),
            }
        )
    state["citations"] = citations
    state["retrieved_docs"] = policy_docs
    state["sql_query"] = kpi.get("sql") or profile.get("sql") or ""
    state["sql_result"] = kpi.get("rows") or profile.get("rows") or []
    state["sql_meta"] = {
        "latency_ms": kpi.get("latency_ms"),
        "supplier_id": sid,
        "bundle": ["profile", "orders", "kpi", "risk", "policy"],
    }

    # Build Document-like objects for evidence helper (duck-typed).
    class _Doc:
        def __init__(self, d: dict):
            self.page_content = d.get("content", "")
            self.metadata = {
                "source_name": d.get("source"),
                "chunk_id": d.get("chunk_id"),
                "doc_type": d.get("doc_type"),
            }

    doc_objs = [_Doc(d) for d in policy_docs]
    kpi_rows = kpi.get("rows") or []
    state["evidence"] = hybrid_evidence(
        docs=doc_objs,
        sql={
            "query": kpi.get("sql") or profile.get("sql") or "",
            "params": {"supplier_id": sid},
            "row_count": len(kpi_rows) or len(profile.get("rows") or []),
            "latency_ms": kpi.get("latency_ms"),
            "metric": "supplier_assessment",
            "metric_definition": "Combined profile, KPI, orders and risk snapshot",
            "formula": "multi-query assessment bundle",
            "time_range": "demo dataset",
            "data_snapshot": RATTI_DATA_SNAPSHOT,
            "sample_size": len(kpi_rows) or len(profile.get("rows") or []),
            "minimum_sample_size": 1,
            "is_sample_sufficient": True,
        },
        sample_size=len(kpi_rows) or len(profile.get("rows") or []),
        minimum_sample_size=1,
        assumptions=["Assessment uses anonymized Ratti demo database."],
        limitations=["Not a formal audit; buyer confirmation required for status changes."],
    )

    lang_instruction = "请用中文撰写结构化评估摘要。" if _zh(state) else "Write the assessment summary in English."
    prompt = ChatPromptTemplate.from_template(SUPPLIER_ASSESSMENT_PROMPT)
    resp = get_llm().invoke(
        prompt.format(
            supplier_id=sid,
            question=state.get("question") or f"Full assessment for {sid}",
            profile_json=json.dumps(profile.get("rows") or [], ensure_ascii=False),
            orders_json=json.dumps(orders.get("rows") or [], ensure_ascii=False),
            kpi_json=json.dumps(kpi.get("rows") or [], ensure_ascii=False),
            risk_json=json.dumps(
                {
                    "risk_events": risk.get("rows") or [],
                    "quality_events": risk.get("quality_rows") or [],
                },
                ensure_ascii=False,
            ),
            policy_excerpts=json.dumps(
                [
                    {"source": d.get("source"), "preview": (d.get("content") or "")[:400]}
                    for d in policy_docs[:5]
                ],
                ensure_ascii=False,
            ),
            response_language_instruction=lang_instruction,
        )
    )
    state["answer"] = resp.content
    state["task_step"] = "synthesize"
    state["confidence"] = max(float(state.get("confidence") or 0.9), 0.9)
    state["reason"] = state.get("reason") or "supplier assessment task"
    return state
