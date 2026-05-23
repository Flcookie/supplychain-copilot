import json
import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from core.config import LLM_MODEL
from core.evidence import document_evidence, hybrid_evidence, simulation_evidence, sql_evidence
from core.qualification_rules import (
    apply_qualification_router_override,
    build_clarification_question,
    extract_qualification_input,
    format_checklist_markdown,
    generate_qualification_checklist,
    needs_category_clarification,
)
from core.prompts import (
    HYBRID_QA_PROMPT,
    KPI_ANSWER_PROMPT,
    KPI_PARSE_PROMPT,
    KPI_SQL_PROMPT,
    KPI_SQL_REPAIR_PROMPT,
    POLICY_QA_PROMPT,
    RAG_FALLBACK_PROMPT,
    ROUTER_PROMPT,
    SCENARIO_ANALYSIS_PROMPT,
)
from rag.retriever import get_retriever
from tools.kpi_sql_builder import TemplatedSQL, build_kpi_sql
from tools.sql_tools import run_sql_query_with_meta
from .state import SCState

llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
retriever = get_retriever()
# Doc-type-scoped retrievers help recall by filtering vector + BM25 to relevant corpora.
policy_retriever = get_retriever(k=5, doc_types=["policy", "contract", "sop", "faq"])
# For hybrid intent we run TWO scoped retrievals and merge — this guarantees that when the
# question references KPI evidence we always include at least one kpi_dict chunk, even if
# vector similarity ranks contracts higher.
hybrid_policy_retriever = get_retriever(k=5, doc_types=["policy", "contract", "sop", "faq"])
hybrid_kpi_retriever = get_retriever(k=2, doc_types=["kpi_dict"])


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


# Metrics the demo schema (suppliers + purchase_orders) cannot answer. We refuse politely
# rather than fabricating numbers from an unrelated table.
UNSUPPORTED_KPI_PATTERNS = {
    "otif": "OTIF requires per-line full-quantity fulfillment data, which the demo schema (suppliers, purchase_orders) does not include.",
    "on-time in full": "OTIF requires per-line full-quantity fulfillment data, which the demo schema does not include.",
    "defect rate": "Defect rate requires a quality / inspection table that is not part of the demo schema.",
    "defect_rate": "Defect rate requires a quality / inspection table that is not part of the demo schema.",
    "risk score": "Supplier risk score requires enterprise risk tables (financial, geopolitical, ESG) that are not part of the demo schema.",
    "risk_score": "Supplier risk score requires enterprise risk tables that are not part of the demo schema.",
    "lead time": "Lead time requires order-creation / acknowledgement timestamps that are not part of the demo schema.",
    "first pass yield": "First-pass yield requires quality inspection data that is not in the demo schema.",
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

    valid_intents = ["policy_qa", "kpi_query", "scenario_analysis", "hybrid_query", "qualification_checklist"]
    if parsed["intent"] not in valid_intents:
        parsed["intent"] = "policy_qa"

    parsed = apply_qualification_router_override(parsed, q)

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
    docs = retriever.invoke(q)
    state["retrieved_docs"] = [
        {"content": d.page_content, "source": d.metadata.get("source_name") or d.metadata.get("source", "")}
        for d in docs
    ]
    state["citations"] = _build_doc_citations(docs)
    state["evidence"] = document_evidence(
        docs,
        evidence_type="hybrid",
        assumptions=["Router confidence was below threshold, so policy context was used as a cautious fallback."],
        limitations=["The answer may be incomplete if the retrieved documents do not cover the requested KPI or scenario."],
    )
    context = "\n\n".join(d.page_content for d in docs)
    prompt = ChatPromptTemplate.from_template(RAG_FALLBACK_PROMPT)
    resp = llm.invoke(
        prompt.format(
            question=q,
            context=context,
            response_language_instruction=_response_language_instruction(state),
        )
    )
    state["fallback_mode"] = "rag_fallback"
    state["answer"] = resp.content
    return state


def policy_qa_node(state: SCState) -> SCState:
    q = state["question"]
    docs = policy_retriever.invoke(q)
    state["retrieved_docs"] = [
        {"content": d.page_content, "source": d.metadata.get("source_name") or d.metadata.get("source", "")}
        for d in docs
    ]
    state["citations"] = _build_doc_citations(docs)
    state["evidence"] = document_evidence(
        docs,
        evidence_type="document",
        limitations=["Policy answers are limited to retrieved demo documents."],
    )
    context = "\n\n".join(d.page_content for d in docs)
    prompt = ChatPromptTemplate.from_template(POLICY_QA_PROMPT)
    resp = llm.invoke(
        prompt.format(
            question=q,
            context=context,
            response_language_instruction=_response_language_instruction(state),
        )
    )
    state["answer"] = resp.content
    return state


def kpi_node(state: SCState) -> SCState:
    q = state["question"]
    parse_prompt = ChatPromptTemplate.from_template(KPI_PARSE_PROMPT)
    parse_raw = llm.invoke(
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
            data_snapshot=metric_meta.get("data_snapshot", "demo SQLite supplychain_kpi.db"),
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

    template = build_kpi_sql(q, kpi_parse)
    sql_source = "template" if template is not None else "llm"
    template_id: str | None = template.template_id if template else None

    if template is not None:
        final_sql = template.sql
        params: tuple | None = template.params
    else:
        prompt = ChatPromptTemplate.from_template(KPI_SQL_PROMPT)
        final_sql = _strip_sql_fences(
            llm.invoke(
                prompt.format(
                    question=q,
                    structured_parse=json.dumps(kpi_parse, ensure_ascii=False),
                )
            ).content
        )
        params = None
    state["sql_query"] = final_sql

    sql_attempts: list[dict] = []
    rows: list = []
    sql_meta: dict | None = None
    last_error: str | None = None

    max_attempts = 1 if template is not None else 2  # templates are pre-validated; only LLM SQL gets repair
    for attempt in range(max_attempts):
        try:
            result = run_sql_query_with_meta(final_sql, params=params)
            rows = result["rows"]
            sql_meta = result["meta"]
            sql_attempts.append(
                {
                    "sql": final_sql,
                    "ok": True,
                    "row_count": sql_meta["row_count"],
                    "source": sql_source if attempt == 0 else "llm_repair",
                }
            )
            last_error = None
            break
        except Exception as e:
            last_error = str(e)
            sql_attempts.append(
                {"sql": final_sql, "ok": False, "error": last_error, "source": sql_source if attempt == 0 else "llm_repair"}
            )
            if attempt == 0 and template is None:
                repair_prompt = ChatPromptTemplate.from_template(KPI_SQL_REPAIR_PROMPT)
                final_sql = _strip_sql_fences(
                    llm.invoke(
                        repair_prompt.format(
                            question=q,
                            failed_sql=final_sql,
                            error=last_error,
                        )
                    ).content
                )
                params = None
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
            query=final_sql,
            params=_params_dict(params),
            row_count=0,
            latency_ms=None,
            metric=kpi_parse.get("metric") or "unknown",
            metric_definition=metric_meta.get("definition", "Metric definition unavailable."),
            formula=metric_meta.get("formula", ""),
            time_range=kpi_parse.get("time_range") or metric_meta.get("default_time_window", "last_3_months"),
            data_snapshot=metric_meta.get("data_snapshot", "demo SQLite supplychain_kpi.db"),
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
    limitations = ["Demo KPI data is small and illustrative, not production supplier performance."]
    if sample_size < minimum_sample_size:
        limitations.append(
            f"Sample size {sample_size} is below the recommended minimum {minimum_sample_size}; treat the result as directional."
        )
    state["evidence"] = sql_evidence(
        query=final_sql,
        params=_params_dict(params),
        row_count=sql_meta.get("row_count", 0),
        latency_ms=sql_meta.get("latency_ms"),
        metric=metric,
        metric_definition=metric_meta.get("definition", "Metric definition unavailable."),
        formula=metric_meta.get("formula", ""),
        time_range=time_range,
        data_snapshot=metric_meta.get("data_snapshot", "demo SQLite supplychain_kpi.db"),
        sample_size=sample_size,
        minimum_sample_size=minimum_sample_size,
        assumptions=assumptions,
        limitations=limitations,
    )
    if state["evidence"].get("sql") is not None:
        state["evidence"]["sql"]["sql_source"] = sql_source
        state["evidence"]["sql"]["template_id"] = template_id
    citation: dict = {
        "type": "sql",
        "sql": final_sql,
        "row_count": sql_meta.get("row_count", 0),
        "latency_ms": sql_meta.get("latency_ms"),
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
    resp = llm.invoke(
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


def hybrid_node(state: SCState) -> SCState:
    """Joint Policy + KPI answer for composite questions.

    The node always retrieves policy/contract evidence for the question, and
    additionally tries the deterministic KPI SQL builder. If a template matches
    the question, it executes that SQL and includes the rows in the prompt.
    """
    q = state["question"]
    policy_docs = hybrid_policy_retriever.invoke(q)
    kpi_docs = hybrid_kpi_retriever.invoke(q)
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
    state["retrieved_docs"] = [
        {"content": d.page_content, "source": d.metadata.get("source_name") or d.metadata.get("source", "")}
        for d in docs
    ]
    citations = _build_doc_citations(docs)

    # Best-effort KPI parse for template matching. Failures degrade gracefully.
    parse_prompt = ChatPromptTemplate.from_template(KPI_PARSE_PROMPT)
    parse_raw = llm.invoke(
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
                data_snapshot=metric_meta.get("data_snapshot", "demo SQLite supplychain_kpi.db"),
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

    policy_context = "\n\n".join(d.page_content for d in docs)
    prompt = ChatPromptTemplate.from_template(HYBRID_QA_PROMPT)
    resp = llm.invoke(
        prompt.format(
            question=q,
            policy_context=policy_context,
            kpi_rows=json.dumps(kpi_rows, ensure_ascii=False),
            kpi_sql=kpi_sql_text or "(no KPI SQL was executed for this question)",
            evidence=json.dumps(state.get("evidence", {}), ensure_ascii=False),
            response_language_instruction=_response_language_instruction(state),
        )
    )
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
    delay_days = int(scenario_spec.get("delay_days") or 7)
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
        verified_facts = _scenario_verified_facts(impact_rows, country, delay_days)
        state["evidence"] = simulation_evidence(
            query=sql.strip(),
            row_count=result["meta"].get("row_count", 0),
            latency_ms=result["meta"].get("latency_ms"),
            params={"country": country, "delay_days": delay_days},
            verified_facts=verified_facts,
            assumptions=[f"If no country is specified, the demo defaults scenario analysis to {country}."],
            limitations=["Scenario recommendations are model-generated based on queried demo order exposure."],
        )
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
        state["evidence"] = simulation_evidence(
            query=sql.strip(),
            row_count=0,
            latency_ms=None,
            params={"country": country, "delay_days": delay_days},
            verified_facts=[f"Scenario SQL failed: {e}"],
            assumptions=[f"If no country is specified, the demo defaults scenario analysis to {country}."],
            limitations=[str(e)],
        )
        state["citations"] = [{"type": "sql", "sql": sql.strip(), "error": str(e)}]

    explain_prompt = ChatPromptTemplate.from_template(SCENARIO_ANALYSIS_PROMPT)
    resp = llm.invoke(
        explain_prompt.format(
            question=q,
            scenario_spec=json.dumps(scenario_spec, ensure_ascii=False),
            impact_rows=json.dumps(impact_rows, ensure_ascii=False),
            verified_facts=json.dumps(state.get("evidence", {}).get("verified_facts", []), ensure_ascii=False),
            response_language_instruction=_response_language_instruction(state),
        )
    )
    state["answer"] = resp.content
    return state


def qualification_checklist_node(state: SCState) -> SCState:
    q = state["question"]
    lang = state.get("response_language", "en") or "en"
    input_data = extract_qualification_input(q)

    if needs_category_clarification(input_data):
        clarification = build_clarification_question(input_data, lang)
        if lang == "zh":
            state["answer"] = (
                f"在进入供应商准入清单前，我需要先确认类别信息。\n\n{clarification}"
            )
        else:
            state["answer"] = (
                f"I need a bit more context before generating your qualification checklist.\n\n{clarification}"
            )
        state["citations"] = []
        state["evidence"] = None
        return state

    checklist = generate_qualification_checklist(input_data)
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
