import json
import os
import re

from langchain_core.prompts import ChatPromptTemplate

from core.demo_constants import DEMO_CURRENT_DATE, RATTI_DATA_SNAPSHOT
from core.entity_parse import classify_risk_question, extract_supplier_id
from core.kpi_parse_utils import normalize_kpi_parse as _normalize_kpi_parse
from core.evidence import document_evidence, hybrid_evidence, simulation_evidence, sql_evidence
from core.llm import get_llm
from core.risk_rules import (
    blacklist_guidance,
    single_sourcing_guidance,
)
from core.router_overrides import apply_lifecycle_router_overrides
from core.qualification_rules import (
    apply_qualification_router_override,
    build_clarification_question,
    extract_qualification_input,
    format_checklist_markdown,
    generate_qualification_checklist,
    needs_category_clarification,
    normalize_qualification_input,
    resolve_response_language,
)
from core.prompt_injection import (
    poisoned_context_refusal,
    prepare_retrieved_context,
    refusal_message,
    sanitize_answer,
    scan_user_input,
    wrap_question_for_prompt,
    wrap_retrieved_context,
)
from core.prompts import (
    HYBRID_AGGREGATE_PROMPT,
    HYBRID_KPI_PARTIAL_PROMPT,
    HYBRID_POLICY_PARTIAL_PROMPT,
    HYBRID_QA_PROMPT,
    KPI_ANSWER_PROMPT,
    KPI_PARSE_PROMPT,
    KPI_SQL_PROMPT,
    KPI_SQL_REPAIR_PROMPT,
    POLICY_QA_PROMPT,
    RAG_FALLBACK_PROMPT,
    ROUTER_PROMPT,
    SCENARIO_ANALYSIS_PROMPT,
    VENDOR_RATING_PROMPT,
)
from core.resilience import (
    BM25_ONLY_LIMITATION_EN,
    BM25_ONLY_LIMITATION_ZH,
    record_resilience_event,
)
from app.services.mcp_client import McpToolError, call_tool, format_tools_for_router, list_tools
from rag.retriever import get_retriever
from tools.kpi_sql_builder import build_kpi_sql
from tools.sql_tools import run_sql_query_with_meta
from .state import SCState


def _retrieval_limitation(state: SCState) -> str:
    return BM25_ONLY_LIMITATION_ZH if state.get("response_language") == "zh" else BM25_ONLY_LIMITATION_EN


def _docs_are_degraded(docs: list) -> bool:
    for doc in docs or []:
        metadata = getattr(doc, "metadata", None)
        if isinstance(metadata, dict) and metadata.get("retrieval_degraded"):
            return True
        if isinstance(doc, dict) and (
            doc.get("retrieval_degraded") or (doc.get("metadata") or {}).get("retrieval_degraded")
        ):
            return True
    return False


def _policy_retriever():
    return get_retriever(k=5, doc_types=["policy", "contract", "sop", "faq"])


def _hybrid_kpi_retriever():
    return get_retriever(k=2, doc_types=["kpi_dict"])


_MCP_TOOLS_BLURB: str | None = None


def _mcp_tool_catalog() -> str:
    """Discover MCP tools once; descriptions are injected into the router prompt."""
    global _MCP_TOOLS_BLURB
    if _MCP_TOOLS_BLURB is not None:
        return _MCP_TOOLS_BLURB
    try:
        _MCP_TOOLS_BLURB = format_tools_for_router(list_tools())
    except Exception as exc:  # noqa: BLE001 — router must not hard-fail if MCP is down
        return f"(MCP tools unavailable: {exc})"
    return _MCP_TOOLS_BLURB


_DATA_SNAPSHOT = RATTI_DATA_SNAPSHOT
_extract_supplier_id = extract_supplier_id
_classify_risk_question = classify_risk_question

_BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def _metrics_dictionary_blurb() -> str:
    data = _metrics_metadata()
    lines = []
    for key, meta in data.items():
        name = meta.get("business_name", key)
        define = meta.get("definition", "")
        formula = meta.get("formula", "")
        lines.append(f"- {key} ({name}): {define}; formula: {formula}")
    return "\n".join(lines)


def _metrics_metadata() -> dict:
    path = os.path.join(_BASE_DIR, "data", "metrics_dictionary.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


def _metric_meta(metric: str | None) -> dict:
    data = _metrics_metadata()
    if metric in data:
        return data[metric]
    if metric in {"comparison", "trend"}:
        return data.get("on_time_rate", {})
    return data.get("on_time_rate", {})


def _estimate_sample_size(rows: list[dict]) -> int:
    if not rows:
        return 0
    total = 0
    saw_count = False
    for row in rows:
        for key in ("total_orders", "total_pos", "order_count", "count"):
            value = row.get(key)
            if isinstance(value, (int, float)):
                total += int(value)
                saw_count = True
                break
    return total if saw_count else len(rows)


def _scenario_verified_facts(rows: list[dict], country: str, delay_days: int) -> list[str]:
    if not rows:
        return [f"No supplier orders were found for country {country} in the demo database."]
    facts = [f"Scenario scope: suppliers in {country}; assumed delay: {delay_days} days."]
    for row in rows:
        supplier = row.get("supplier_name", "Unknown supplier")
        total_pos = row.get("total_pos", 0)
        total_qty = row.get("total_qty", 0)
        facts.append(f"{supplier}: {total_pos} affected purchase orders, total quantity {total_qty}.")
    return facts


def _extract_recommendation_lines(answer: str) -> list[str]:
    recommendations = []
    for line in answer.splitlines():
        stripped = line.strip().lstrip("-*0123456789. ")
        if not stripped:
            continue
        lower = stripped.lower()
        if any(token in lower for token in ["recommend", "mitigation", "safety stock", "backup", "review", "建议", "缓解", "库存", "备选"]):
            recommendations.append(stripped)
    return recommendations[:5]


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
    if ambiguity_type == "overbroad_data_request":
        return "Please specify a supplier ID, category, time period, or metric. I cannot dump the entire database."
    return "Could you clarify your request so I can answer precisely?"


def _response_language_instruction(state: SCState) -> str:
    return "professional Chinese" if state.get("response_language", "en") == "zh" else "concise professional English"


def _strip_sql_fences(sql: str) -> str:
    """Remove ```sql ... ``` fences and stray whitespace that LLMs sometimes emit."""
    cleaned = sql.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("sql"):
            cleaned = cleaned[3:]
    return cleaned.strip().strip("`").strip()


def _params_dict(params: tuple | None) -> dict:
    """Render parameterized SQL params into a JSON-friendly dict for evidence/citations."""
    if not params:
        return {}
    return {f"p{i}": value for i, value in enumerate(params, start=1)}


# OTIF still requires line-level full-quantity data not modeled in Ratti demo.
UNSUPPORTED_KPI_PATTERNS = {
    "otif": "OTIF requires per-line full-quantity fulfillment data, which the Ratti demo schema does not include.",
    "on-time in full": "OTIF requires per-line full-quantity fulfillment data, which the Ratti demo schema does not include.",
}


def _detect_unsupported_metric(question: str) -> str | None:
    lowered = (question or "").lower()
    for token, reason in UNSUPPORTED_KPI_PATTERNS.items():
        if token in lowered:
            return reason
    return None


def _build_doc_citations(docs: list) -> list:
    citations = []
    for i, doc in enumerate(docs, start=1):
        citations.append(
            {
                "type": "document",
                "source": doc.metadata.get("source_name") or doc.metadata.get("source", ""),
                "chunk_id": doc.metadata.get("chunk_id") or f"doc-{i}",
                "clause": doc.metadata.get("section_title") or doc.metadata.get("section", ""),
                "doc_type": doc.metadata.get("doc_type", ""),
                "retrieval_score": doc.metadata.get("retrieval_score"),
            }
        )
    return citations


def router_node(state: SCState) -> SCState:
    q = state["question"]

    # API-forced intents (SkillHub workflow skills / assessment entry): keep seed.
    if state.get("baseline_mode") and state.get("intent"):
        seeded = state["intent"]
        supplier_id = state.get("supplier_id") or _extract_supplier_id(q)
        if supplier_id:
            state["supplier_id"] = supplier_id
            if seeded == "supplier_assessment":
                state["ambiguity_type"] = None
        elif seeded == "supplier_assessment" and not state.get("ambiguity_type"):
            state["ambiguity_type"] = "missing_entity"
        state["confidence"] = float(state.get("confidence") or 0.99)
        if seeded == "supplier_assessment":
            state["task_type"] = "supplier_assessment"
        state["reason"] = state.get("reason") or f"api forced_intent={seeded}"
        state["fallback_mode"] = "none"
        state["route_decision"] = {
            "intent": seeded,
            "confidence": state["confidence"],
            "ambiguity_type": state.get("ambiguity_type"),
            "human_approval_required": False,
            "reason": state["reason"],
            "supplier_id": state.get("supplier_id"),
        }
        return state

    prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT)
    resp = get_llm().invoke(prompt.format(question=q, mcp_tools=_mcp_tool_catalog()))

    parsed = {
        "intent": "policy_qa",
        "confidence": 0.6,
        "ambiguity_type": None,
        "human_approval_required": False,
        "reason": "router defaulted due to unparsable output",
    }
    try:
        llm_result = _safe_json_load(resp.content.strip())
        parsed["intent"] = llm_result.get("intent", parsed["intent"])
        parsed["confidence"] = float(llm_result.get("confidence", parsed["confidence"]))
        parsed["ambiguity_type"] = llm_result.get("ambiguity_type")
        parsed["human_approval_required"] = bool(llm_result.get("human_approval_required", False))
        parsed["reason"] = llm_result.get("reason", parsed["reason"])
    except Exception:
        pass

    if parsed["intent"] == "scenario_analysis":
        parsed["intent"] = "risk_scenario"

    valid_intents = [
        "policy_qa",
        "kpi_query",
        "risk_scenario",
        "scenario_analysis",
        "hybrid_query",
        "qualification_checklist",
        "vendor_rating_explanation",
        "supplier_assessment",
    ]
    if parsed["intent"] not in valid_intents:
        parsed["intent"] = "policy_qa"

    parsed = apply_qualification_router_override(parsed, q)
    parsed = apply_lifecycle_router_overrides(parsed, q)

    # Persist supplier entity when present for checkpoint / assessment.
    supplier_id = _extract_supplier_id(q)
    if supplier_id:
        state["supplier_id"] = supplier_id

    state["intent"] = parsed["intent"]
    state["confidence"] = max(0.0, min(parsed["confidence"], 1.0))
    state["ambiguity_type"] = parsed["ambiguity_type"]
    state["human_approval_required"] = parsed.get("human_approval_required", False)
    state["reason"] = parsed["reason"]
    state["fallback_mode"] = "none"
    state["task_type"] = (
        "supplier_assessment" if parsed["intent"] == "supplier_assessment" else state.get("task_type") or "chat"
    )
    state["route_decision"] = {
        "intent": state["intent"],
        "confidence": state["confidence"],
        "ambiguity_type": state["ambiguity_type"],
        "human_approval_required": state.get("human_approval_required"),
        "reason": state["reason"],
        "supplier_id": state.get("supplier_id"),
    }
    try:
        from observability.recorder import record_step

        record_step(
            "router_decision",
            detail={
                "kind": "router",
                "intent": state["intent"],
                "confidence": state["confidence"],
                "ambiguity_type": state.get("ambiguity_type"),
                "human_approval_required": state.get("human_approval_required"),
            },
        )
    except Exception:  # noqa: BLE001
        pass
    if (
        not state.get("ambiguity_type")
        and float(state.get("confidence") or 0) < 0.75
        and not state.get("baseline_mode")
    ):
        record_resilience_event(
            "fallback",
            from_backend="specialist_route",
            to_backend="rag_fallback",
            reason=f"router_confidence={state.get('confidence')}<0.75",
        )
    return state

def clarification_node(state: SCState) -> SCState:
    is_zh = state.get("response_language", "en") == "zh"
    clarification = _build_clarification_question(state.get("ambiguity_type"))
    if is_zh:
        clarification_map = {
            "When you say 'they/this supplier', which supplier are you referring to?": "你提到的“他们/这家供应商”具体指哪一家？",
            "Do you want policy standards first, or supplier KPI data first?": "你是想先看政策标准，还是先看供应商KPI数据？",
            "Please specify supplier name and time range (for example: Alpha, last 3 months).": "请补充供应商名称和时间范围（例如：Alpha，最近3个月）。",
            "Could you clarify your request so I can answer precisely?": "请补充更多信息，我才能给出准确回答。",
        }
        clarification = clarification_map.get(clarification, clarification)
    state["clarification_question"] = clarification
    state["answer"] = (
        f"在进入下一步前，我需要先确认一个信息。\n\n{clarification}\n\n请补充后我会继续处理。"
        if is_zh
        else f"I need one clarification before routing this request.\n\n{clarification}\n\nReply with the missing details and I will continue."
    )
    return state


def rag_fallback_node(state: SCState) -> SCState:
    q = state["question"]
    lang = state.get("response_language") or "en"
    docs = get_retriever().invoke(q)
    prepared = prepare_retrieved_context(docs)
    docs = prepared["kept"]
    if prepared["all_poisoned"]:
        state["injection_blocked"] = True
        state["answer"] = poisoned_context_refusal(lang)
        state["retrieved_docs"] = []
        state["citations"] = []
        state["evidence"] = {
            "type": "hybrid",
            "limitations": prepared["limitations"] or ["Retrieved context was excluded as indirect injection."],
        }
        return state
    state["retrieved_docs"] = [
        {"content": d.page_content, "source": d.metadata.get("source_name") or d.metadata.get("source", "")}
        for d in docs
    ]
    state["citations"] = _build_doc_citations(docs)
    limitations = [
        "The answer may be incomplete if the retrieved documents do not cover the requested KPI or scenario.",
        *prepared["limitations"],
    ]
    state["evidence"] = document_evidence(
        docs,
        evidence_type="hybrid",
        assumptions=["Router confidence was below threshold, so policy context was used as a cautious fallback."],
        limitations=limitations,
    )
    if _docs_are_degraded(docs):
        extra = list(state["evidence"].get("limitations") or [])
        extra.append(_retrieval_limitation(state))
        state["evidence"]["limitations"] = extra
    prompt = ChatPromptTemplate.from_template(RAG_FALLBACK_PROMPT)
    resp = get_llm().invoke(
        prompt.format(
            question=wrap_question_for_prompt(q),
            context=prepared["context"],
            response_language_instruction=_response_language_instruction(state),
        )
    )
    state["fallback_mode"] = "rag_fallback"
    state["answer"] = resp.content
    return state


def policy_qa_node(state: SCState) -> SCState:
    q = state["question"]
    lang = state.get("response_language") or "en"

    scan = scan_user_input(q)
    state["injection_scan"] = {
        "is_injection": scan.is_injection,
        "should_refuse": scan.should_refuse,
        "reasons": list(scan.reasons),
        "primary_attack": scan.primary_attack,
    }
    if scan.should_refuse:
        state["injection_blocked"] = True
        state["answer"] = refusal_message(lang)
        state["retrieved_docs"] = []
        state["citations"] = []
        state["evidence"] = {
            "type": "document",
            "limitations": [
                "Blocked by prompt-injection guard before retrieval.",
                *list(scan.reasons),
            ],
            "assumptions": [],
        }
        return state

    # MCP client: call_tool("query_policy") instead of hard-coded retriever.invoke.
    try:
        payload = call_tool("query_policy", {"query": q, "k": 5})
    except McpToolError as exc:
        state["answer"] = f"Policy retrieval failed via MCP: {exc.message}"
        state["retrieved_docs"] = []
        state["citations"] = []
        state["evidence"] = {
            "type": "document",
            "limitations": [exc.message],
        }
        return state

    if not isinstance(payload, dict):
        payload = {}
    documents = payload.get("documents") or []

    # Adapt MCP JSON docs into the lightweight Document-like objects evidence helpers expect.
    class _Doc:
        def __init__(self, item: dict):
            self.page_content = item.get("content", "")
            self.metadata = {
                "source_name": item.get("source", ""),
                "source": item.get("source", ""),
                "doc_type": item.get("doc_type", ""),
                "retrieval_score": item.get("retrieval_score"),
                "retrieval_degraded": item.get("retrieval_degraded"),
                "retrieval_mode": item.get("retrieval_mode"),
            }

    docs = [_Doc(item) for item in documents if isinstance(item, dict)]
    prepared = prepare_retrieved_context(docs)
    docs = prepared["kept"]
    if prepared["all_poisoned"]:
        state["injection_blocked"] = True
        state["answer"] = poisoned_context_refusal(lang)
        state["retrieved_docs"] = []
        state["citations"] = []
        state["evidence"] = {
            "type": "document",
            "limitations": prepared["limitations"] or ["Retrieved context was excluded as indirect injection."],
            "assumptions": [],
        }
        return state

    state["retrieved_docs"] = [
        {"content": d.page_content, "source": d.metadata.get("source_name") or d.metadata.get("source", "")}
        for d in docs
    ]
    state["citations"] = _build_doc_citations(docs)
    limitations = ["Policy answers are limited to retrieved demo documents (via MCP query_policy)."]
    limitations.extend(prepared["limitations"])
    degraded = bool(payload.get("retrieval_degraded")) or _docs_are_degraded(docs)
    if degraded:
        limitations.append(_retrieval_limitation(state))
    state["evidence"] = document_evidence(
        docs,
        evidence_type="document",
        limitations=limitations,
    )
    prompt = ChatPromptTemplate.from_template(POLICY_QA_PROMPT)
    resp = get_llm().invoke(
        prompt.format(
            question=wrap_question_for_prompt(q),
            context=prepared["context"],
            response_language_instruction=_response_language_instruction(state),
        )
    )
    cleaned, redactions = sanitize_answer(resp.content if isinstance(resp.content, str) else str(resp.content))
    state["answer"] = cleaned
    if degraded:
        note = _retrieval_limitation(state)
        if note not in state["answer"]:
            state["answer"] = state["answer"].rstrip() + "\n\n_" + note + "_"
    if redactions and isinstance(state.get("evidence"), dict):
        limitations = list(state["evidence"].get("limitations") or [])
        limitations.append(f"Output sanitizer redacted {len(redactions)} sensitive field pattern(s).")
        state["evidence"]["limitations"] = limitations
    return state


def kpi_node(state: SCState) -> SCState:
    q = state["question"]
    parse_prompt = ChatPromptTemplate.from_template(KPI_PARSE_PROMPT)
    parse_raw = get_llm().invoke(
        parse_prompt.format(question=q, metrics_blurb=_metrics_dictionary_blurb())
    ).content.strip()
    kpi_parse: dict = {
        "intent": "KPI_Query",
        "supplier_hint": None,
        "metric": "other",
        "time_range": None,
        "aggregation": "other",
        "need_clarification": False,
        "clarification_reason": None,
    }
    try:
        kpi_parse.update(_safe_json_load(parse_raw))
    except Exception:
        pass
    kpi_parse = _normalize_kpi_parse(q, kpi_parse)
    state["kpi_parse"] = kpi_parse

    unsupported_reason = _detect_unsupported_metric(q)
    if unsupported_reason is not None:
        # Generate a structured refusal answer; the metric is not in the demo schema.
        metric_meta = _metric_meta(kpi_parse.get("metric"))
        state["sql_query"] = None
        state["sql_result"] = []
        state["sql_meta"] = None
        state["evidence"] = sql_evidence(
            query="-- refusal: metric not supported by demo schema --",
            params={},
            row_count=0,
            latency_ms=None,
            metric=kpi_parse.get("metric") or "unsupported",
            metric_definition=unsupported_reason,
            formula="n/a",
            time_range=kpi_parse.get("time_range") or "n/a",
            data_snapshot=metric_meta.get("data_snapshot", _DATA_SNAPSHOT),
            sample_size=0,
            minimum_sample_size=int(metric_meta.get("minimum_sample_size", 1)),
            assumptions=["Demo schema only contains suppliers and purchase_orders; KPIs requiring extra tables cannot be computed."],
            limitations=[unsupported_reason],
        )
        if state["evidence"].get("sql") is not None:
            state["evidence"]["sql"]["sql_source"] = "refusal"
            state["evidence"]["sql"]["template_id"] = None
        is_zh = state.get("response_language", "en") == "zh"
        if is_zh:
            state["answer"] = (
                "我无法基于当前 demo 数据计算这个指标。\n\n"
                f"原因：{unsupported_reason}\n\n"
                "建议：升级到包含相关原始数据的企业表（例如质量检测、风险评估、订单确认时间戳）后再回答。"
            )
        else:
            state["answer"] = (
                "I cannot compute this metric from the current demo data.\n\n"
                f"Reason: {unsupported_reason}\n\n"
                "Recommendation: Upgrade the data source to enterprise tables that include the underlying data (e.g. quality inspection, risk assessment, order acknowledgement timestamps)."
            )
        state["citations"] = [
            {
                "type": "sql",
                "sql": "-- refusal: metric not supported by demo schema --",
                "row_count": 0,
                "sql_source": "refusal",
                "template_id": None,
                "reason": unsupported_reason,
            }
        ]
        return state

    # MCP client path: structured query_kpi first; NL2SQL fallback passes sql= through the same tool.
    supplier_hint = (kpi_parse.get("supplier_hint") or "") or ""
    supplier_id = _extract_supplier_id(q) or _extract_supplier_id(supplier_hint) or ""
    metric = kpi_parse.get("metric") or ""
    if metric in {"other", "comparison", "trend"}:
        metric_arg = ""
    else:
        metric_arg = metric
    time_range = kpi_parse.get("time_range") or ""

    sql_attempts: list[dict] = []
    rows: list = []
    sql_meta: dict | None = None
    last_error: str | None = None
    final_sql: str | None = None
    sql_source = "template"
    template_id: str | None = None
    params: tuple | None = None

    try:
        payload = call_tool(
            "query_kpi",
            {
                "supplier_id": supplier_id,
                "metric": metric_arg,
                "time_range": time_range,
                "question": q,
            },
        )
        if not isinstance(payload, dict):
            raise McpToolError("query_kpi", "MCP returned a non-object payload")
        final_sql = payload.get("sql")
        rows = payload.get("rows") or []
        sql_meta = payload.get("meta") or {"row_count": len(rows), "latency_ms": None}
        sql_source = payload.get("sql_source") or "template"
        template_id = payload.get("template_id")
        params_map = payload.get("params") or {}
        params = tuple(params_map.values()) if params_map else None
        state["sql_query"] = final_sql
        sql_attempts.append(
            {
                "sql": final_sql,
                "ok": True,
                "row_count": sql_meta.get("row_count", len(rows)),
                "source": sql_source,
            }
        )
        last_error = None
    except McpToolError as mcp_exc:
        last_error = mcp_exc.message
        sql_attempts.append(
            {"sql": None, "ok": False, "error": last_error, "source": "mcp_template"}
        )
        # NL2SQL fallback: LLM writes SQL, MCP executes it (allowlisted read-only).
        prompt = ChatPromptTemplate.from_template(KPI_SQL_PROMPT)
        final_sql = _strip_sql_fences(
            get_llm().invoke(
                prompt.format(
                    question=q,
                    structured_parse=json.dumps(kpi_parse, ensure_ascii=False),
                )
            ).content
        )
        params = None
        sql_source = "llm"
        template_id = None
        state["sql_query"] = final_sql

        for attempt in range(2):
            try:
                payload = call_tool(
                    "query_kpi",
                    {
                        "supplier_id": supplier_id,
                        "metric": metric_arg,
                        "time_range": time_range,
                        "question": q,
                        "sql": final_sql,
                    },
                )
                if not isinstance(payload, dict):
                    raise McpToolError("query_kpi", "MCP returned a non-object payload")
                rows = payload.get("rows") or []
                sql_meta = payload.get("meta") or {"row_count": len(rows), "latency_ms": None}
                final_sql = payload.get("sql") or final_sql
                sql_source = payload.get("sql_source") or sql_source
                state["sql_query"] = final_sql
                sql_attempts.append(
                    {
                        "sql": final_sql,
                        "ok": True,
                        "row_count": sql_meta.get("row_count", len(rows)),
                        "source": sql_source if attempt == 0 else "llm_repair",
                    }
                )
                last_error = None
                break
            except McpToolError as exec_exc:
                last_error = exec_exc.message
                sql_attempts.append(
                    {
                        "sql": final_sql,
                        "ok": False,
                        "error": last_error,
                        "source": sql_source if attempt == 0 else "llm_repair",
                    }
                )
                if attempt == 0:
                    record_resilience_event(
                        "retry_repair",
                        from_backend="nl2sql",
                        to_backend="nl2sql_repair_once",
                        reason=last_error,
                    )
                    repair_prompt = ChatPromptTemplate.from_template(KPI_SQL_REPAIR_PROMPT)
                    final_sql = _strip_sql_fences(
                        get_llm().invoke(
                            repair_prompt.format(
                                question=q,
                                failed_sql=final_sql,
                                error=last_error,
                            )
                        ).content
                    )
                    sql_source = "llm_repair"
                    state["sql_query"] = final_sql
                else:
                    break

    if last_error is not None:
        state["answer"] = (
            f"Error while running KPI query: {last_error}\n\nLast attempted SQL:\n```sql\n{final_sql}\n```"
        )
        state["sql_result"] = []
        state["sql_meta"] = {"row_count": 0, "latency_ms": None, "error": last_error}
        metric_meta = _metric_meta(kpi_parse.get("metric"))
        state["evidence"] = sql_evidence(
            query=final_sql or "-- mcp query_kpi failed --",
            params=_params_dict(params),
            row_count=0,
            latency_ms=None,
            metric=kpi_parse.get("metric") or "unknown",
            metric_definition=metric_meta.get("definition", "Metric definition unavailable."),
            formula=metric_meta.get("formula", ""),
            time_range=kpi_parse.get("time_range") or metric_meta.get("default_time_window", "last_3_months"),
            data_snapshot=metric_meta.get("data_snapshot", _DATA_SNAPSHOT),
            sample_size=0,
            minimum_sample_size=int(metric_meta.get("minimum_sample_size", 1)),
            assumptions=["KPI execution failed before a result could be verified."],
            limitations=[last_error],
        )
        if state["evidence"].get("sql") is not None:
            state["evidence"]["sql"]["sql_source"] = sql_source
            state["evidence"]["sql"]["template_id"] = template_id
        state["citations"] = [
            {
                "type": "sql",
                "sql": final_sql,
                "row_count": 0,
                "latency_ms": None,
                "error": last_error,
                "attempts": sql_attempts,
                "sql_source": sql_source,
                "template_id": template_id,
            }
        ]
        return state

    state["sql_result"] = rows
    state["sql_meta"] = sql_meta
    metric = kpi_parse.get("metric") or "on_time_rate"
    metric_meta = _metric_meta(metric)
    sample_size = _estimate_sample_size(rows)
    minimum_sample_size = int(metric_meta.get("minimum_sample_size", 1))
    time_range = kpi_parse.get("time_range") or metric_meta.get("default_time_window", "last_3_months")
    assumptions = []
    if not kpi_parse.get("time_range"):
        assumptions.append(f"No time range was specified; defaulted to {time_range}.")
    limitations = [
        "Anonymized synthetic Ratti demo dataset for product prototyping — not production supplier performance.",
        f"Demo sample: {sample_size} record(s) returned; treat as illustrative only.",
        "KPI rows executed via MCP tool query_kpi.",
    ]
    state["evidence"] = sql_evidence(
        query=final_sql or "",
        params=_params_dict(params),
        row_count=(sql_meta or {}).get("row_count", 0),
        latency_ms=(sql_meta or {}).get("latency_ms"),
        metric=metric,
        metric_definition=metric_meta.get("definition", "Metric definition unavailable."),
        formula=metric_meta.get("formula", ""),
        time_range=time_range,
        data_snapshot=metric_meta.get("data_snapshot", "demo SQLite ratti_copilot_demo.db"),
        sample_size=sample_size,
        minimum_sample_size=minimum_sample_size,
        assumptions=assumptions,
        limitations=limitations,
    )
    if state["evidence"].get("sql") is not None:
        state["evidence"]["sql"]["sql_source"] = sql_source
        state["evidence"]["sql"]["template_id"] = template_id
        state["evidence"]["sql"]["is_sample_sufficient"] = False
        state["evidence"]["is_sample_sufficient"] = False
    citation: dict = {
        "type": "sql",
        "sql": final_sql,
        "row_count": (sql_meta or {}).get("row_count", 0),
        "latency_ms": (sql_meta or {}).get("latency_ms"),
        "metric_definition": metric_meta.get("definition", ""),
        "time_range": time_range,
        "sample_size": sample_size,
        "sql_source": sql_source,
        "template_id": template_id,
    }
    if len(sql_attempts) > 1:
        citation["attempts"] = sql_attempts
        citation["repaired"] = True
    state["citations"] = [citation]

    explain_prompt = ChatPromptTemplate.from_template(KPI_ANSWER_PROMPT)
    resp = get_llm().invoke(
        explain_prompt.format(
            question=q,
            sql=final_sql,
            rows=json.dumps(rows, ensure_ascii=False),
            evidence=json.dumps(state.get("evidence", {}), ensure_ascii=False),
            response_language_instruction=_response_language_instruction(state),
        )
    )
    state["answer"] = resp.content
    if state.get("evidence") is not None:
        state["evidence"]["recommendations"] = _extract_recommendation_lines(resp.content)
    return state



def hybrid_dispatch_node(state: SCState) -> SCState:
    """Fan-out marker: LangGraph runs hybrid_policy ∥ hybrid_kpi after this node."""
    q = state.get("question") or ""
    scan = scan_user_input(q)
    update: dict = {
        "hybrid_parallel": True,
        "injection_scan": {
            "is_injection": scan.is_injection,
            "should_refuse": scan.should_refuse,
            "reasons": list(scan.reasons),
            "primary_attack": scan.primary_attack,
        },
    }
    if scan.should_refuse:
        refusal = refusal_message(state.get("response_language") or "en")
        update.update(
            {
                "injection_blocked": True,
                "policy_partial_answer": refusal,
                "kpi_partial_answer": "",
                "answer": refusal,
                "retrieved_docs": [],
                "citations": [],
                "evidence": {
                    "type": "hybrid",
                    "limitations": [
                        "Blocked by prompt-injection guard before hybrid fan-out.",
                        *list(scan.reasons),
                    ],
                },
            }
        )
    return update  # type: ignore[return-value]


def hybrid_policy_branch(state: SCState) -> dict:
    """Parallel policy branch for hybrid_query (retrieval + partial answer)."""
    if state.get("injection_blocked"):
        return {}

    q = state["question"]
    lang = state.get("response_language") or "en"
    policy_docs = _policy_retriever().invoke(q)
    prepared = prepare_retrieved_context(policy_docs)
    if prepared["all_poisoned"]:
        refusal = poisoned_context_refusal(lang)
        return {
            "injection_blocked": True,
            "policy_partial_answer": refusal,
            "answer": refusal,
            "retrieved_docs": [],
            "citations": [],
            "evidence": {
                "type": "hybrid",
                "limitations": prepared["limitations"]
                or ["Retrieved context was excluded as indirect injection."],
            },
        }
    policy_docs = prepared["kept"]
    docs_meta = [
        {
            "content": d.page_content,
            "metadata": dict(d.metadata or {}),
        }
        for d in policy_docs
    ]
    prompt = ChatPromptTemplate.from_template(HYBRID_POLICY_PARTIAL_PROMPT)
    resp = get_llm().invoke(
        prompt.format(
            question=wrap_question_for_prompt(q),
            context=prepared["context"],
            response_language_instruction=_response_language_instruction(state),
        )
    )
    partial = resp.content if isinstance(resp.content, str) else str(resp.content)
    cleaned, _ = sanitize_answer(partial)
    return {
        "policy_partial_answer": cleaned,
        "hybrid_policy_docs": docs_meta,
    }


def hybrid_kpi_branch(state: SCState) -> dict:
    """Parallel KPI branch for hybrid_query (parse + template SQL + partial answer)."""
    if state.get("injection_blocked"):
        return {}

    q = state["question"]
    # Soft signal from kpi_dict retrieval (not merged into shared lists here to avoid races).
    _ = _hybrid_kpi_retriever().invoke(q)

    parse_prompt = ChatPromptTemplate.from_template(KPI_PARSE_PROMPT)
    parse_raw = get_llm().invoke(
        parse_prompt.format(question=q, metrics_blurb=_metrics_dictionary_blurb())
    ).content.strip()
    kpi_parse: dict = {
        "intent": "KPI_Query",
        "supplier_hint": None,
        "metric": "other",
        "time_range": None,
        "aggregation": "other",
    }
    try:
        kpi_parse.update(_safe_json_load(parse_raw))
    except Exception:
        pass
    kpi_parse = _normalize_kpi_parse(q, kpi_parse)

    template = build_kpi_sql(q, kpi_parse)
    kpi_rows: list = []
    kpi_sql_text = ""
    sql_evidence_payload = None
    sample_size = None
    minimum_sample_size = 1
    sql_meta_for_state = None
    sql_citation = None

    if template is not None:
        try:
            result = run_sql_query_with_meta(template.sql, params=template.params)
            kpi_rows = result["rows"]
            kpi_sql_text = template.sql
            metric = kpi_parse.get("metric") or "on_time_rate"
            metric_meta = _metric_meta(metric)
            sample_size = _estimate_sample_size(kpi_rows)
            minimum_sample_size = int(metric_meta.get("minimum_sample_size", 1))
            time_range = kpi_parse.get("time_range") or metric_meta.get("default_time_window", "last_3_months")
            sql_evidence_payload = sql_evidence(
                query=template.sql,
                params=_params_dict(template.params),
                row_count=result["meta"].get("row_count", 0),
                latency_ms=result["meta"].get("latency_ms"),
                metric=metric,
                metric_definition=metric_meta.get("definition", "Metric definition unavailable."),
                formula=metric_meta.get("formula", ""),
                time_range=time_range,
                data_snapshot=metric_meta.get("data_snapshot", _DATA_SNAPSHOT),
                sample_size=sample_size,
                minimum_sample_size=minimum_sample_size,
                assumptions=[f"KPI branch used deterministic template `{template.template_id}`."],
                limitations=["Demo KPI dataset; treat numbers as illustrative."],
            )["sql"]
            sql_evidence_payload["sql_source"] = "template"
            sql_evidence_payload["template_id"] = template.template_id
            sql_meta_for_state = result["meta"]
            sql_citation = {
                "type": "sql",
                "sql": template.sql,
                "row_count": result["meta"].get("row_count", 0),
                "latency_ms": result["meta"].get("latency_ms"),
                "sample_size": sample_size,
                "sql_source": "template",
                "template_id": template.template_id,
                "branch": "kpi",
            }
        except Exception as exc:
            sql_citation = {"type": "sql", "sql": template.sql, "error": str(exc), "branch": "kpi"}

    prompt = ChatPromptTemplate.from_template(HYBRID_KPI_PARTIAL_PROMPT)
    resp = get_llm().invoke(
        prompt.format(
            question=wrap_question_for_prompt(q),
            kpi_rows=json.dumps(kpi_rows, ensure_ascii=False),
            kpi_sql=kpi_sql_text or "(no KPI SQL was executed for this question)",
            response_language_instruction=_response_language_instruction(state),
        )
    )
    partial = resp.content if isinstance(resp.content, str) else str(resp.content)
    update: dict = {
        "kpi_parse": kpi_parse,
        "kpi_partial_answer": partial,
        "sql_query": kpi_sql_text or None,
        "sql_result": kpi_rows,
        "sql_meta": sql_meta_for_state,
        "hybrid_sql_evidence": sql_evidence_payload,
        "hybrid_sample_size": sample_size,
        "hybrid_minimum_sample_size": minimum_sample_size,
    }
    if sql_citation is not None:
        update["citations"] = [sql_citation]
    return update


def hybrid_aggregate_node(state: SCState) -> dict:
    """Join node: merge parallel policy + KPI branch results."""
    if state.get("injection_blocked") and state.get("answer"):
        return {}

    q = state["question"]
    policy_partial = state.get("policy_partial_answer") or "(policy branch produced no result)"
    kpi_partial = state.get("kpi_partial_answer") or "(kpi branch produced no result)"

    class _Doc:
        def __init__(self, item: dict):
            self.page_content = item.get("content", "")
            self.metadata = item.get("metadata") or {}

    meta_docs = state.get("hybrid_policy_docs") or []
    docs = [_Doc(item) for item in meta_docs if isinstance(item, dict)]

    sample_size = state.get("hybrid_sample_size")
    minimum_sample_size = state.get("hybrid_minimum_sample_size") or 1
    sql_evidence_payload = state.get("hybrid_sql_evidence")

    evidence = hybrid_evidence(
        docs=docs,
        sql=sql_evidence_payload,
        sample_size=sample_size,
        minimum_sample_size=minimum_sample_size,
        assumptions=[
            "Hybrid answers fuse parallel Policy and KPI branches, then aggregate.",
        ],
        limitations=[
            "If no KPI template matches, the KPI branch may return empty numeric evidence.",
        ],
    )
    if _docs_are_degraded(docs):
        limitations = list(evidence.get("limitations") or [])
        limitations.append(_retrieval_limitation(state))
        evidence["limitations"] = limitations

    prompt = ChatPromptTemplate.from_template(HYBRID_AGGREGATE_PROMPT)
    resp = get_llm().invoke(
        prompt.format(
            question=wrap_question_for_prompt(q),
            policy_partial=policy_partial,
            kpi_partial=kpi_partial,
            evidence=json.dumps(evidence, ensure_ascii=False),
            response_language_instruction=_response_language_instruction(state),
        )
    )
    cleaned, redactions = sanitize_answer(resp.content if isinstance(resp.content, str) else str(resp.content))
    if redactions:
        limitations = list(evidence.get("limitations") or [])
        limitations.append(f"Output sanitizer redacted {len(redactions)} sensitive field pattern(s).")
        evidence["limitations"] = limitations

    doc_citations = _build_doc_citations(docs)
    existing_citations = list(state.get("citations") or [])
    # Prefer SQL citations from KPI branch + document citations from policy branch.
    merged_citations = existing_citations + [
        c for c in doc_citations if c not in existing_citations
    ]

    return {
        "answer": cleaned,
        "evidence": evidence,
        "retrieved_docs": [
            {
                "content": d.page_content,
                "source": d.metadata.get("source_name") or d.metadata.get("source", ""),
                "branch": "policy",
            }
            for d in docs
        ],
        "citations": merged_citations,
        "hybrid_parallel": True,
    }


def hybrid_node(state: SCState) -> SCState:
    """Legacy sequential hybrid (kept for smoke tests / baseline). Prefer parallel graph path."""
    q = state["question"]
    scan = scan_user_input(q)
    state["injection_scan"] = {
        "is_injection": scan.is_injection,
        "should_refuse": scan.should_refuse,
        "reasons": list(scan.reasons),
        "primary_attack": scan.primary_attack,
    }
    if scan.should_refuse:
        state["injection_blocked"] = True
        state["answer"] = refusal_message(state.get("response_language") or "en")
        state["retrieved_docs"] = []
        state["citations"] = []
        state["evidence"] = {
            "type": "hybrid",
            "limitations": ["Blocked by prompt-injection guard.", *list(scan.reasons)],
        }
        return state

    policy_docs = _policy_retriever().invoke(q)
    kpi_docs = _hybrid_kpi_retriever().invoke(q)
    # Interleave so at least one kpi_dict chunk lands in the top-5 evidence list.
    # Layout: policy[0..3] | kpi[0..1] | remaining policy.
    seen_keys: set = set()
    docs: list = []

    def _push(d):
        key = d.metadata.get("chunk_id") or id(d)
        if key in seen_keys:
            return
        docs.append(d)
        seen_keys.add(key)

    for d in policy_docs[:4]:
        _push(d)
    for d in kpi_docs[:2]:
        _push(d)
    for d in policy_docs[4:]:
        _push(d)
    prepared = prepare_retrieved_context(docs)
    if prepared["all_poisoned"]:
        state["injection_blocked"] = True
        state["answer"] = poisoned_context_refusal(state.get("response_language") or "en")
        state["retrieved_docs"] = []
        state["citations"] = []
        state["evidence"] = {
            "type": "hybrid",
            "limitations": prepared["limitations"]
            or ["Retrieved context was excluded as indirect injection."],
        }
        return state
    docs = prepared["kept"]
    state["retrieved_docs"] = [
        {"content": d.page_content, "source": d.metadata.get("source_name") or d.metadata.get("source", "")}
        for d in docs
    ]
    citations = _build_doc_citations(docs)

    # Best-effort KPI parse for template matching. Failures degrade gracefully.
    parse_prompt = ChatPromptTemplate.from_template(KPI_PARSE_PROMPT)
    parse_raw = get_llm().invoke(
        parse_prompt.format(question=q, metrics_blurb=_metrics_dictionary_blurb())
    ).content.strip()
    kpi_parse: dict = {
        "intent": "KPI_Query",
        "supplier_hint": None,
        "metric": "other",
        "time_range": None,
        "aggregation": "other",
    }
    try:
        kpi_parse.update(_safe_json_load(parse_raw))
    except Exception:
        pass
    kpi_parse = _normalize_kpi_parse(q, kpi_parse)
    state["kpi_parse"] = kpi_parse

    template = build_kpi_sql(q, kpi_parse)
    kpi_rows: list = []
    kpi_sql_text = ""
    sql_evidence_payload = None
    sample_size = None
    minimum_sample_size = 1
    sql_meta_for_state = None
    if template is not None:
        try:
            result = run_sql_query_with_meta(template.sql, params=template.params)
            kpi_rows = result["rows"]
            kpi_sql_text = template.sql
            metric = kpi_parse.get("metric") or "on_time_rate"
            metric_meta = _metric_meta(metric)
            sample_size = _estimate_sample_size(kpi_rows)
            minimum_sample_size = int(metric_meta.get("minimum_sample_size", 1))
            time_range = kpi_parse.get("time_range") or metric_meta.get("default_time_window", "last_3_months")
            sql_evidence_payload = sql_evidence(
                query=template.sql,
                params=_params_dict(template.params),
                row_count=result["meta"].get("row_count", 0),
                latency_ms=result["meta"].get("latency_ms"),
                metric=metric,
                metric_definition=metric_meta.get("definition", "Metric definition unavailable."),
                formula=metric_meta.get("formula", ""),
                time_range=time_range,
                data_snapshot=metric_meta.get("data_snapshot", _DATA_SNAPSHOT),
                sample_size=sample_size,
                minimum_sample_size=minimum_sample_size,
                assumptions=[f"KPI sub-answer used deterministic template `{template.template_id}`."],
                limitations=["Demo KPI dataset; treat numbers as illustrative."],
            )["sql"]
            sql_evidence_payload["sql_source"] = "template"
            sql_evidence_payload["template_id"] = template.template_id
            sql_meta_for_state = result["meta"]
            citations.append(
                {
                    "type": "sql",
                    "sql": template.sql,
                    "row_count": result["meta"].get("row_count", 0),
                    "latency_ms": result["meta"].get("latency_ms"),
                    "sample_size": sample_size,
                    "sql_source": "template",
                    "template_id": template.template_id,
                }
            )
        except Exception as exc:
            citations.append({"type": "sql", "sql": template.sql, "error": str(exc)})

    state["sql_query"] = kpi_sql_text or None
    state["sql_result"] = kpi_rows
    state["sql_meta"] = sql_meta_for_state
    state["citations"] = citations

    state["evidence"] = hybrid_evidence(
        docs=docs,
        sql=sql_evidence_payload,
        sample_size=sample_size,
        minimum_sample_size=minimum_sample_size,
        assumptions=[
            "Hybrid answers fuse policy/contract evidence with KPI SQL when a deterministic template matches the question."
        ],
        limitations=[
            "If no KPI template matches, the answer relies on retrieved policy evidence only and may not include numeric KPI claims."
        ],
    )

    policy_context = wrap_retrieved_context("\n\n".join(d.page_content for d in docs))
    prompt = ChatPromptTemplate.from_template(HYBRID_QA_PROMPT)
    resp = get_llm().invoke(
        prompt.format(
            question=wrap_question_for_prompt(q),
            policy_context=policy_context,
            kpi_rows=json.dumps(kpi_rows, ensure_ascii=False),
            kpi_sql=kpi_sql_text or "(no KPI SQL was executed for this question)",
            evidence=json.dumps(state.get("evidence", {}), ensure_ascii=False),
            response_language_instruction=_response_language_instruction(state),
        )
    )
    cleaned, redactions = sanitize_answer(resp.content if isinstance(resp.content, str) else str(resp.content))
    state["answer"] = cleaned
    if redactions and isinstance(state.get("evidence"), dict):
        limitations = list(state["evidence"].get("limitations") or [])
        limitations.append(f"Output sanitizer redacted {len(redactions)} sensitive field pattern(s).")
        state["evidence"]["limitations"] = limitations
    return state


def scenario_node(state: SCState) -> SCState:
    """Risk scenario analysis: review lists, quality issues, what-if delay, blacklist HITL."""
    q = state["question"]
    risk_type = _classify_risk_question(q)
    human_approval = bool(state.get("human_approval_required")) or risk_type == "blacklist"
    scenario_spec = {"risk_type": risk_type, "human_approval_required": human_approval}
    state["scenario_spec"] = scenario_spec

    impact_rows: list[dict] = []
    sql = ""
    params: tuple | dict = ()

    relaxed_rows: list[dict] = []
    if risk_type == "review_due":
        sql = """
SELECT DISTINCT s.supplier_id,
       s.supplier_name_anonymized,
       s.risk_level,
       s.kraljic_quadrant,
       s.next_review_date,
       s.qualification_status
FROM suppliers s
LEFT JOIN risk_events r ON s.supplier_id = r.supplier_id
WHERE (s.risk_level IN ('High', 'Medium') OR r.risk_score_1_25 >= 15)
  AND s.next_review_date >= date(?, 'start of month')
  AND s.next_review_date < date(?, 'start of month', '+1 month')
ORDER BY s.risk_level DESC, s.next_review_date ASC
"""
        params = (DEMO_CURRENT_DATE, DEMO_CURRENT_DATE)
    elif risk_type == "quality_issues":
        supplier_id = _extract_supplier_id(q) or "SUP021"
        sql = """
SELECT q.quality_event_id,
       q.event_date,
       q.non_conformity_type,
       q.severity,
       q.defect_rate,
       q.corrective_action_required,
       s.supplier_id,
       s.category_level_2,
       s.kraljic_quadrant,
       s.risk_level,
       vr.rating_class
FROM quality_events q
JOIN suppliers s ON q.supplier_id = s.supplier_id
LEFT JOIN vendor_rating vr ON s.supplier_id = vr.supplier_id
WHERE s.supplier_id = ?
ORDER BY q.event_date DESC
"""
        params = (supplier_id,)
        scenario_spec["supplier_id"] = supplier_id
    elif risk_type == "blacklist":
        supplier_id = _extract_supplier_id(q) or "SUP030"
        sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       s.risk_level,
       s.qualification_status,
       s.supply_risk_score,
       r.risk_type,
       r.risk_score_1_25,
       r.recommended_action,
       r.human_review_required
FROM suppliers s
LEFT JOIN risk_events r ON s.supplier_id = r.supplier_id
WHERE s.supplier_id = ?
ORDER BY r.risk_score_1_25 DESC
"""
        params = (supplier_id,)
        scenario_spec["supplier_id"] = supplier_id
    elif risk_type == "single_sourcing":
        sql = """
SELECT supplier_id,
       supplier_name_anonymized,
       category_level_2,
       kraljic_quadrant,
       single_sourcing_flag,
       risk_level,
       qualification_status
FROM suppliers
WHERE single_sourcing_flag = 1
  AND category_level_2 LIKE '%Outsourced Fabric%'
ORDER BY supply_risk_score DESC
"""
        params = ()
    else:
        delay_days = 7
        if "delay" in q.lower():
            delay_match = re.search(r"(\d+)\s*day", q.lower())
            if delay_match:
                delay_days = int(delay_match.group(1))
        scenario_spec["delay_days"] = delay_days
        category = "Yarns" if "yarn" in q.lower() else None
        if category:
            sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       s.category_level_2,
       COUNT(p.po_id) AS affected_pos,
       ROUND(SUM(p.order_amount_eur), 2) AS total_amount_eur
FROM suppliers s
JOIN purchase_orders p ON s.supplier_id = p.supplier_id
WHERE s.kraljic_quadrant = 'Strategic'
  AND s.category_level_2 = ?
GROUP BY s.supplier_id, s.supplier_name_anonymized, s.category_level_2
"""
            params = (category,)
        else:
            sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       s.country,
       COUNT(p.po_id) AS affected_pos,
       ROUND(SUM(p.order_amount_eur), 2) AS total_amount_eur
FROM suppliers s
JOIN purchase_orders p ON s.supplier_id = p.supplier_id
WHERE s.risk_level IN ('High', 'Medium')
GROUP BY s.supplier_id, s.supplier_name_anonymized, s.country
ORDER BY total_amount_eur DESC
"""
            params = ()

    try:
        result = run_sql_query_with_meta(sql, params=params if isinstance(params, tuple) else None)
        impact_rows = result["rows"]
        executed = result["meta"].get("executed_sql", sql.strip())
        state["sql_query"] = executed
        state["sql_result"] = impact_rows
        state["sql_meta"] = result["meta"]
    except Exception as e:
        impact_rows = [{"error": str(e)}]
        state["sql_query"] = sql.strip()
        state["sql_result"] = []
        state["sql_meta"] = {"row_count": 0, "error": str(e)}

    if risk_type == "review_due" and len(impact_rows) == 0:
        relaxed_sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       s.risk_level,
       s.kraljic_quadrant,
       s.next_review_date,
       s.qualification_status
FROM suppliers s
WHERE s.risk_level IN ('High', 'Medium')
  AND (
        s.next_review_date < date(?, 'start of month')
        OR s.next_review_date >= date(?, 'start of month', '+1 month')
      )
ORDER BY s.supply_risk_score DESC
LIMIT 10
"""
        try:
            relaxed_rows = run_sql_query_with_meta(
                relaxed_sql, params=(DEMO_CURRENT_DATE, DEMO_CURRENT_DATE)
            )["rows"]
        except Exception:
            relaxed_rows = []

    verified_facts = []
    if risk_type == "single_sourcing":
        verified_facts = [
            f"Found {len(impact_rows)} single-sourced outsourced fabric processing suppliers in demo data."
        ] + single_sourcing_guidance()[:2]
    elif impact_rows and "error" not in impact_rows[0]:
        verified_facts.append(f"Risk scenario type: {risk_type}; rows returned: {len(impact_rows)}.")
        for row in impact_rows[:5]:
            sid = row.get("supplier_id", row.get("supplier_name_anonymized", "unknown"))
            verified_facts.append(f"Supplier {sid}: risk_level={row.get('risk_level', 'n/a')}, rating={row.get('rating_class', 'n/a')}.")
    else:
        verified_facts.append("No matching risk records found in demo database.")

    if human_approval:
        verified_facts.extend(blacklist_guidance()[:2])

    state["evidence"] = simulation_evidence(
        query=sql.strip(),
        row_count=len(impact_rows) if impact_rows else 0,
        latency_ms=state.get("sql_meta", {}).get("latency_ms"),
        params=scenario_spec,
        verified_facts=verified_facts,
        assumptions=["Risk recommendations combine SQL facts with Ratti procurement policy templates."],
        limitations=[
            "Anonymized synthetic Ratti demo data; final decisions require buyer/manager approval.",
            f"Demo as-of date for calendar filters: {DEMO_CURRENT_DATE}.",
        ],
    )
    state["citations"] = [{"type": "sql", "sql": state.get("sql_query"), "row_count": len(impact_rows)}]

    explain_prompt = ChatPromptTemplate.from_template(SCENARIO_ANALYSIS_PROMPT)
    resp = get_llm().invoke(
        explain_prompt.format(
            question=q,
            scenario_spec=json.dumps(scenario_spec, ensure_ascii=False),
            impact_rows=json.dumps(impact_rows, ensure_ascii=False),
            relaxed_rows=json.dumps(relaxed_rows, ensure_ascii=False),
            verified_facts=json.dumps(verified_facts, ensure_ascii=False),
            response_language_instruction=_response_language_instruction(state),
        )
    )
    answer = resp.content
    if human_approval:
        hitl = (
            "\n\n**Human approval required:** AI can recommend actions only; procurement manager must confirm blacklist or status changes."
            if state.get("response_language", "en") == "en"
            else "\n\n**需人工确认：** AI 仅可给出建议，黑名单或状态变更须由采购经理审批。"
        )
        answer += hitl
    state["answer"] = answer
    state["human_approval_required"] = human_approval
    return state


def vendor_rating_node(state: SCState) -> SCState:
    q = state["question"]
    human_approval = bool(state.get("human_approval_required")) or (
        "reserve" in q.lower() and "qualified" in q.lower()
    )
    supplier_id = _extract_supplier_id(q)

    # Formula-only questions: use policy RAG context via retriever
    if supplier_id is None and ("formula" in q.lower() or "weight" in q.lower()):
        docs = _policy_retriever().invoke(q)
        prepared = prepare_retrieved_context(docs)
        docs = prepared["kept"]
        if prepared["all_poisoned"]:
            state["injection_blocked"] = True
            state["answer"] = poisoned_context_refusal(state.get("response_language") or "en")
            state["retrieved_docs"] = []
            state["citations"] = []
            state["evidence"] = {
                "type": "document",
                "limitations": prepared["limitations"]
                or ["Retrieved context was excluded as indirect injection."],
            }
            return state
        state["retrieved_docs"] = [
            {"content": d.page_content, "source": d.metadata.get("source_name") or d.metadata.get("source", "")}
            for d in docs
        ]
        state["citations"] = _build_doc_citations(docs)
        prompt = ChatPromptTemplate.from_template(POLICY_QA_PROMPT)
        resp = get_llm().invoke(
            prompt.format(
                question=wrap_question_for_prompt(q),
                context=prepared["context"],
                response_language_instruction=_response_language_instruction(state),
            )
        )
        state["answer"] = resp.content
        state["evidence"] = document_evidence(docs, evidence_type="document")
        return state

    if "reserve" in q.lower() and supplier_id is None:
        sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       s.qualification_status,
       vr.rating_class,
       vr.final_vendor_rating_score,
       s.risk_level,
       vr.suggested_action
FROM suppliers s
JOIN vendor_rating vr ON s.supplier_id = vr.supplier_id
WHERE s.qualification_status = 'Qualified'
  AND (vr.rating_class IN ('C', 'D') OR s.risk_level = 'High')
ORDER BY vr.final_vendor_rating_score ASC
"""
        rating_rows = run_sql_query_with_meta(sql)["rows"]
        support_rows = []
        state["sql_query"] = sql.strip()
        state["sql_result"] = rating_rows
    elif supplier_id:
        rating_sql = """
SELECT vr.*, s.supplier_name_anonymized, s.category_level_2, s.kraljic_quadrant, s.qualification_status
FROM vendor_rating vr
JOIN suppliers s ON vr.supplier_id = s.supplier_id
WHERE vr.supplier_id = ?
ORDER BY vr.period DESC
LIMIT 1
"""
        rating_rows = run_sql_query_with_meta(rating_sql, params=(supplier_id,))["rows"]
        support_sql = """
SELECT 'delivery' AS source,
       ROUND(AVG(delivery_delay_days), 2) AS avg_delay,
       ROUND(AVG(on_time_flag) * 100, 2) AS otd_pct
FROM delivery_events WHERE supplier_id = ?
UNION ALL
SELECT 'quality' AS source,
       ROUND(AVG(defect_rate) * 100, 2) AS avg_defect_pct,
       COUNT(*) AS event_count
FROM quality_events WHERE supplier_id = ?
"""
        try:
            support_rows = run_sql_query_with_meta(support_sql, params=(supplier_id, supplier_id))["rows"]
        except Exception:
            support_rows = []
        state["sql_query"] = rating_sql.strip()
        state["sql_result"] = rating_rows
    else:
        state["answer"] = "Please provide a supplier ID (e.g. SUP012) so I can explain the vendor rating."
        return state

    state["citations"] = [{"type": "sql", "sql": state.get("sql_query", ""), "row_count": len(rating_rows)}]
    metric_meta = _metric_meta("vendor_rating")
    state["evidence"] = sql_evidence(
        query=state.get("sql_query") or "-- vendor rating lookup --",
        params={"supplier_id": supplier_id},
        row_count=len(rating_rows),
        latency_ms=None,
        metric="vendor_rating",
        metric_definition=metric_meta.get("definition", ""),
        formula=metric_meta.get("formula", ""),
        time_range="2025",
        data_snapshot=_DATA_SNAPSHOT,
        sample_size=len(rating_rows),
        minimum_sample_size=1,
        limitations=["Vendor rating explanation uses synthetic Ratti demo data."],
    )

    explain_prompt = ChatPromptTemplate.from_template(VENDOR_RATING_PROMPT)
    resp = get_llm().invoke(
        explain_prompt.format(
            question=q,
            rating_rows=json.dumps(rating_rows, ensure_ascii=False),
            support_rows=json.dumps(support_rows if supplier_id else rating_rows, ensure_ascii=False),
            response_language_instruction=_response_language_instruction(state),
        )
    )
    answer = resp.content
    if human_approval:
        hitl = (
            "\n\n**Human approval required:** Status changes (e.g. Qualified → Qualified with Reserve) require buyer confirmation."
            if state.get("response_language", "en") == "en"
            else "\n\n**需人工确认：** 状态变更（如 Qualified → Qualified with Reserve）须采购员确认。"
        )
        answer += hitl
    state["answer"] = answer
    state["human_approval_required"] = human_approval
    return state


def qualification_checklist_node(state: SCState) -> SCState:
    q = state["question"]
    lang = resolve_response_language(state.get("response_language"), q)
    input_data = extract_qualification_input(q)

    if needs_category_clarification(input_data):
        clarification = build_clarification_question(input_data, lang)
        if lang == "zh":
            state["answer"] = clarification
        else:
            state["answer"] = (
                f"I need a bit more context before generating your qualification checklist.\n\n{clarification}"
            )
        state["citations"] = []
        state["evidence"] = None
        return state

    input_data = normalize_qualification_input(input_data)
    checklist = generate_qualification_checklist(input_data, lang=lang)
    state["answer"] = format_checklist_markdown(checklist, lang)
    state["citations"] = [
        {
            "type": "qualification_checklist",
            "recommended_category": checklist.get("recommended_category"),
            "kraljic_classification": checklist.get("kraljic_classification"),
            "monitoring_frequency": checklist.get("monitoring_frequency"),
        }
    ]
    return state


def answer_node(state: SCState) -> SCState:
    if "citations" not in state:
        state["citations"] = []
    return state
