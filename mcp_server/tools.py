"""Shared implementations behind MCP tools (also usable in-process for tests)."""

from __future__ import annotations

import json
import re
from typing import Any

from tools.kpi_sql_builder import build_kpi_sql
from tools.sql_tools import run_sql_query_with_meta

_SUPPLIER_ID_PATTERN = re.compile(r"\b(SUP\d{3})\b", re.IGNORECASE)

SUPPORTED_METRICS = (
    "on_time_rate",
    "defect_rate",
    "avg_delay_days",
    "spend",
    "esg_score",
    "vendor_rating",
    "cert_expiry",
    "supplier_status",
)


class ToolValidationError(ValueError):
    """Invalid tool arguments — mapped to MCP isError responses by the server."""


def query_policy_impl(query: str, k: int = 5) -> dict[str, Any]:
    """Hybrid RAG over Pinecone (policy/contract/sop/faq). Returns retrieved chunks."""
    if not (query or "").strip():
        raise ToolValidationError("query must be a non-empty string.")
    if k < 1 or k > 20:
        raise ToolValidationError("k must be between 1 and 20.")

    # Lazy import so KPI-only paths / list_tools don't require Pinecone at import time.
    from rag.retriever import get_retriever

    retriever = get_retriever(k=k, doc_types=["policy", "contract", "sop", "faq"])
    docs = retriever.invoke(query.strip())
    degraded = bool(getattr(retriever, "last_degraded", False)) or any(
        bool(d.metadata.get("retrieval_degraded")) for d in docs
    )
    documents = [
        {
            "content": d.page_content,
            "source": d.metadata.get("source_name") or d.metadata.get("source", ""),
            "doc_type": d.metadata.get("doc_type", ""),
            "retrieval_score": d.metadata.get("retrieval_score"),
            "retrieval_mode": d.metadata.get("retrieval_mode"),
            "retrieval_degraded": bool(d.metadata.get("retrieval_degraded")),
        }
        for d in docs
    ]
    payload: dict[str, Any] = {
        "documents": documents,
        "context": "\n\n".join(d.page_content for d in docs),
        "count": len(documents),
        "retrieval_mode": "bm25_only" if degraded else "hybrid",
        "retrieval_degraded": degraded,
    }
    if degraded:
        from core.resilience import BM25_ONLY_LIMITATION_EN

        payload["retrieval_limitation"] = BM25_ONLY_LIMITATION_EN
    return payload


def query_kpi_impl(
    supplier_id: str = "",
    metric: str = "",
    time_range: str = "",
    question: str = "",
    sql: str = "",
) -> dict[str, Any]:
    """Execute a KPI query via deterministic SQL templates or validated read-only SQL.

    Prefer structured args (supplier_id / metric / time_range). Pass ``sql`` only when
    the Copilot LLM has already generated a SELECT (NL2SQL fallback / repair).
    """
    supplier_id = (supplier_id or "").strip().upper()
    metric = (metric or "").strip()
    time_range = (time_range or "").strip()
    question = (question or "").strip()
    sql = (sql or "").strip()

    if sql:
        try:
            result = run_sql_query_with_meta(sql)
        except ValueError as exc:
            raise ToolValidationError(str(exc)) from exc
        except Exception as exc:
            raise ToolValidationError(f"SQL execution failed: {exc}") from exc
        return {
            "ok": True,
            "sql": sql,
            "sql_source": "llm",
            "template_id": None,
            "params": {},
            "rows": result["rows"],
            "meta": result["meta"],
            "supplier_id": supplier_id or None,
            "metric": metric or None,
            "time_range": time_range or None,
        }

    if not metric and not question:
        raise ToolValidationError(
            "query_kpi requires metric (or question), or an explicit sql string. "
            f"Supported metrics: {', '.join(SUPPORTED_METRICS)}."
        )

    if metric and metric not in SUPPORTED_METRICS and metric not in {"other", "comparison", "trend"}:
        raise ToolValidationError(
            f"Unsupported metric '{metric}'. Supported: {', '.join(SUPPORTED_METRICS)}."
        )

    if supplier_id and not _SUPPLIER_ID_PATTERN.fullmatch(supplier_id):
        raise ToolValidationError(
            f"Invalid supplier_id '{supplier_id}'. Expected form SUP### (e.g. SUP012)."
        )

    synthetic_question = question or " ".join(
        part for part in [metric.replace("_", " "), supplier_id, time_range] if part
    )
    kpi_parse = {
        "intent": "KPI_Query",
        "supplier_hint": supplier_id or None,
        "metric": metric or "other",
        "time_range": time_range or None,
        "aggregation": "other",
        "need_clarification": False,
        "clarification_reason": None,
    }

    template = build_kpi_sql(synthetic_question, kpi_parse)
    if template is None:
        raise ToolValidationError(
            "No KPI SQL template matched the given arguments. "
            f"supplier_id={supplier_id!r}, metric={metric!r}, time_range={time_range!r}. "
            "Provide a more specific metric/supplier_id, or pass a validated read-only sql string."
        )

    try:
        result = run_sql_query_with_meta(template.sql, params=template.params)
    except ValueError as exc:
        raise ToolValidationError(str(exc)) from exc
    except Exception as exc:
        raise ToolValidationError(f"SQL execution failed: {exc}") from exc

    params_dict = {f"p{i}": v for i, v in enumerate(template.params or ())}
    return {
        "ok": True,
        "sql": template.sql,
        "sql_source": "template",
        "template_id": template.template_id,
        "description": template.description,
        "params": params_dict,
        "rows": result["rows"],
        "meta": result["meta"],
        "supplier_id": supplier_id or None,
        "metric": metric or None,
        "time_range": time_range or None,
        "kpi_parse": kpi_parse,
    }


def score_supplier_risk_impl(supplier_id: str = "", as_of_date: str = "") -> dict[str, Any]:
    """Weighted risk score from risk_events + quality_events + document expiry."""
    supplier_id = (supplier_id or "").strip().upper()
    if not _SUPPLIER_ID_PATTERN.fullmatch(supplier_id):
        raise ToolValidationError(
            f"Invalid supplier_id '{supplier_id}'. Expected form SUP### (e.g. SUP018)."
        )

    as_of = (as_of_date or "").strip() or None
    # Prefer demo snapshot date when caller omits as_of
    if not as_of:
        try:
            from core.demo_constants import DEMO_CURRENT_DATE

            as_of = DEMO_CURRENT_DATE
        except Exception:  # noqa: BLE001
            as_of = "2025-12-31"

    risk_sql = """
SELECT COUNT(*) AS n,
       COALESCE(AVG(risk_score_1_25), 0) AS avg_score,
       COALESCE(MAX(risk_score_1_25), 0) AS max_score
FROM risk_events
WHERE supplier_id = ?
"""
    quality_sql = """
SELECT COUNT(*) AS n,
       COALESCE(AVG(defect_rate), 0) AS avg_defect
FROM quality_events
WHERE supplier_id = ?
"""
    docs_sql = """
SELECT COUNT(*) AS expired_or_soon
FROM documents
WHERE supplier_id = ?
  AND (
    LOWER(COALESCE(document_status, '')) IN ('expired', 'invalid')
    OR (expiry_date IS NOT NULL AND expiry_date <= date(?, '+30 days'))
  )
"""
    risk = run_sql_query_with_meta(risk_sql, params=(supplier_id,))
    quality = run_sql_query_with_meta(quality_sql, params=(supplier_id,))
    docs = run_sql_query_with_meta(docs_sql, params=(supplier_id, as_of))

    r = (risk.get("rows") or [{}])[0]
    q = (quality.get("rows") or [{}])[0]
    d = (docs.get("rows") or [{}])[0]

    risk_n = float(r.get("n") or 0)
    risk_avg = float(r.get("avg_score") or 0)  # 1-25
    risk_max = float(r.get("max_score") or 0)
    q_n = float(q.get("n") or 0)
    defect = float(q.get("avg_defect") or 0)  # 0-1
    expired = float(d.get("expired_or_soon") or 0)

    # Map components to 0-100 then weight
    risk_component = min(100.0, (risk_avg / 25.0) * 70.0 + min(risk_n, 5) * 6.0)
    quality_component = min(100.0, defect * 100.0 * 0.7 + min(q_n, 8) * 4.0)
    cert_component = min(100.0, expired * 25.0)

    score = round(
        0.45 * risk_component + 0.35 * quality_component + 0.20 * cert_component,
        1,
    )
    if score >= 70:
        band = "high"
    elif score >= 40:
        band = "medium"
    else:
        band = "low"

    drivers: list[str] = []
    if risk_max >= 15 or risk_n >= 2:
        drivers.append("risk_events")
    if defect >= 0.05 or q_n >= 3:
        drivers.append("quality_defect_signal")
    if expired >= 1:
        drivers.append("cert_expiring_or_invalid")
    if not drivers:
        drivers.append("baseline")

    events_sql = """
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
    quality_events_sql = """
SELECT quality_event_id, event_date, non_conformity_type, severity, defect_rate
FROM quality_events
WHERE supplier_id = ?
ORDER BY event_date DESC
LIMIT 5
"""
    events = run_sql_query_with_meta(events_sql, params=(supplier_id,))
    quality_events = run_sql_query_with_meta(quality_events_sql, params=(supplier_id,))

    return {
        "supplier_id": supplier_id,
        "as_of_date": as_of,
        "risk_score": score,
        "band": band,
        "drivers": drivers,
        "components": {
            "risk_events": {
                "count": int(risk_n),
                "avg_score_1_25": round(risk_avg, 2),
                "max_score_1_25": round(risk_max, 2),
                "contribution": round(risk_component, 1),
            },
            "quality_events": {
                "count": int(q_n),
                "avg_defect_rate": round(defect, 4),
                "contribution": round(quality_component, 1),
            },
            "documents": {
                "expired_or_soon": int(expired),
                "contribution": round(cert_component, 1),
            },
        },
        "events": events.get("rows") or [],
        "quality_events": quality_events.get("rows") or [],
        "events_sql": events_sql.strip(),
        "source": "mcp:score_supplier_risk",
    }


def dumps_tool_result(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)
