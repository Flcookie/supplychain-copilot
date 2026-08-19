import sys, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import time

import streamlit as st

from api.scenarios import DEMO_SCENARIOS
from api.services.copilot import (
    graph_cache_key,
    merge_clarification_reply,
    run_copilot,
    resume_thread,
    get_thread_state,
)
from core.demo_constants import RATTI_DATA_SNAPSHOT

st.markdown(
    "<style> .stChatMessage {font-size: 16px;} </style>", unsafe_allow_html=True
)

# Graph cache key lives in api.services.copilot


def _graph_cache_key() -> str:
    return graph_cache_key()


@st.cache_resource(show_spinner="Loading SupplyChain Copilot...")
def get_graph(_cache_key: str):
    from api.services.copilot import get_graph as _get_graph

    return _get_graph(_cache_key)


graph = get_graph(_graph_cache_key())

I18N = {
    "en": {
        "sidebar_title": "### Supplier Lifecycle Copilot",
        "sidebar_desc": """

        **Core capabilities:**

        1. Supplier qualification checklist

        2. Policy and ESG Q&A

        3. Supplier KPI query

        4. Risk review and scenario analysis

        5. Vendor rating explanation

        """,
        "scenario_templates": "Scenario templates",
        "human_approval_warning": "Human approval required — AI recommends only; buyer/manager must confirm status or blacklist decisions.",
        "paused_hitl": "Graph paused — approve keeps the recommendation; reject parks it. No database write.",
        "approve": "Approve",
        "reject": "Reject",
        "hitl_note": "Optional approval note",
        "title_tagline": "AI decision-support system for Ratti-style supplier management",
        "source_expander": "Referenced documents",
        "debug_expander": "Debug (router & trace)",
        "evidence_expander": "Evidence (SQL & data)",
        "evidence_summary": "Evidence summary",
        "calculation_expander": "Calculation logic",
        "limitations_expander": "Limitations and assumptions",
        "verified_facts": "Verified facts",
        "recommendations": "Recommended actions",
        "source_label": "Source",
        "chat_input": "Ask about qualification, policies, KPIs, risk, or vendor ratings...",
        "analyzing": "Analyzing your question...",
        "copilot": "**Copilot**",
        "current_task": "Current task",
        "intent_label": "Intent",
        "confidence_label": "Confidence",
        "language_label": "Language",
        "metric": "Metric",
        "definition": "Definition",
        "time_range": "Time range",
        "rows": "Rows returned",
        "sample_size": "Sample size",
        "formula": "Formula",
        "data_snapshot": "Data source",
        "assumptions": "Assumptions",
        "limitations": "Limitations",
        "type": "Evidence type",
    },
    "zh": {
        "sidebar_title": "### Supplier Lifecycle Copilot",
        "sidebar_desc": """

        **核心能力：**

        1. 供应商准入清单

        2. 政策与 ESG 问答

        3. 供应商 KPI 查询

        4. 风险复审与情景分析

        5. Vendor Rating 解释

        """,
        "scenario_templates": "场景模板",
        "human_approval_warning": "需人工确认 — AI 仅可建议，状态变更或黑名单须采购经理审批。",
        "paused_hitl": "工作流已暂停 — 批准仅保留建议，驳回则搁置。不会写库。",
        "approve": "批准",
        "reject": "驳回",
        "hitl_note": "可选审批备注",
        "title_tagline": "面向 Ratti 供应商管理场景的 AI 决策辅助系统",
        "source_expander": "引用文档",
        "debug_expander": "调试信息（路由与追踪）",
        "evidence_expander": "证据（SQL 与数据）",
        "evidence_summary": "证据摘要",
        "calculation_expander": "计算说明",
        "limitations_expander": "限制与假设",
        "verified_facts": "已验证事实",
        "recommendations": "建议动作",
        "source_label": "来源",
        "chat_input": "请输入准入、政策、KPI、风险或评分相关问题...",
        "analyzing": "正在分析你的问题...",
        "copilot": "**Copilot**",
        "current_task": "当前任务",
        "intent_label": "意图",
        "confidence_label": "置信度",
        "language_label": "语言",
        "metric": "指标",
        "definition": "定义",
        "time_range": "时间范围",
        "rows": "返回行数",
        "sample_size": "样本量",
        "formula": "公式",
        "data_snapshot": "数据来源",
        "assumptions": "假设",
        "limitations": "限制",
        "type": "证据类型",
    },
}

# ---------------- Streamlit Config ----------------

st.set_page_config(
    page_title="Supplier Lifecycle Copilot",
    page_icon="🟢",
    layout="wide",
)

# ---------------- Sidebar ----------------

with st.sidebar:

    lang_option = st.radio("Language / 语言", ["English", "中文"], horizontal=True)

    lang = "zh" if lang_option == "中文" else "en"

    t = I18N[lang]

    st.markdown(t["sidebar_title"])

    st.markdown(t["sidebar_desc"])

    st.markdown("---")

    demo_options = DEMO_SCENARIOS[lang]

    demo_labels = [label for label, _ in demo_options]

    selected_demo = st.selectbox(t["scenario_templates"], demo_labels, index=0)

    demo_question = dict(demo_options).get(selected_demo, "")

    if demo_question and st.session_state.get("last_demo_label") != selected_demo:

        st.session_state.last_demo_label = selected_demo

        st.session_state.pending_demo_question = demo_question

# ---------------- Session State ----------------

if "messages" not in st.session_state:

    st.session_state.messages = []

if "clarification_base_question" not in st.session_state:

    st.session_state.clarification_base_question = None

if "pending_demo_question" not in st.session_state:

    st.session_state.pending_demo_question = None

if "last_demo_label" not in st.session_state:

    st.session_state.last_demo_label = None

if "thread_id" not in st.session_state:
    import uuid as _uuid

    q_thread = st.query_params.get("thread")
    st.session_state.thread_id = q_thread or str(_uuid.uuid4())
    if q_thread:
        try:
            snap = get_thread_state(q_thread)
            if snap.get("paused") or "approval" in (snap.get("next") or []):
                values = snap.get("values") or {}
                interrupt = snap.get("interrupt") or {}
                st.session_state.paused = True
                if not st.session_state.messages:
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": values.get("answer")
                            or interrupt.get("draft_preview")
                            or interrupt.get("message")
                            or "Waiting for buyer approval.",
                            "intent": values.get("intent"),
                            "route_info": {
                                "intent": values.get("intent"),
                                "human_approval_required": True,
                                "paused": True,
                                "proposed_action": values.get("proposed_action")
                                or interrupt.get("proposed_action"),
                                "task_step": "awaiting_approval",
                                "supplier_id": values.get("supplier_id"),
                            },
                            "sources": [],
                            "citations": values.get("citations") or [],
                            "evidence": values.get("evidence") or {},
                            "paused": True,
                            "interrupt": interrupt,
                            "lang": lang,
                        }
                    )
        except Exception:
            pass

if "paused" not in st.session_state:

    st.session_state.paused = False

if st.session_state.thread_id:
    st.query_params["thread"] = st.session_state.thread_id

# ---------------- Title ----------------
# Use native widgets — indented HTML inside st.markdown() is parsed as a code block.
st.title("Supplier Lifecycle Copilot")
st.markdown(t["title_tagline"])


_INTENT_LABELS = {
    "en": {
        "policy_qa": "Policy Q&A",
        "kpi_query": "KPI Query",
        "risk_scenario": "Risk Review",
        "scenario_analysis": "Risk Review",
        "hybrid_query": "Policy + KPI",
        "qualification_checklist": "Qualification",
        "vendor_rating_explanation": "Vendor Rating",
        "general": "General",
    },
    "zh": {
        "policy_qa": "政策问答",
        "kpi_query": "KPI 查询",
        "risk_scenario": "风险复审",
        "scenario_analysis": "风险复审",
        "hybrid_query": "政策+KPI",
        "qualification_checklist": "准入清单",
        "vendor_rating_explanation": "评分解释",
        "general": "通用",
    },
}

_BADGE_COLORS = {
    "policy_qa": "green",
    "kpi_query": "blue",
    "risk_scenario": "orange",
    "scenario_analysis": "orange",
    "hybrid_query": "violet",
    "qualification_checklist": "green",
    "vendor_rating_explanation": "orange",
}


def get_intent_label(intent: str, lang_code: str = "en") -> str:
    intent = (intent or "policy_qa").lower()
    lang_labels = _INTENT_LABELS.get(lang_code, _INTENT_LABELS["en"])
    return lang_labels.get(intent, lang_labels["general"])


def render_current_task(route_info: dict, msg_t: dict, lang_code: str):
    if not route_info:
        return
    intent = route_info.get("intent") or "unknown"
    confidence = route_info.get("confidence")
    conf_txt = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "—"
    label = get_intent_label(intent, lang_code)
    badge_color = _BADGE_COLORS.get(intent, "gray")
    row = st.container(horizontal=True, vertical_alignment="center")
    with row:
        st.caption(f"**{msg_t['current_task']}**")
        st.badge(label, color=badge_color)
        st.caption(
            f"{msg_t['intent_label']}: `{intent}` · {msg_t['confidence_label']}: **{conf_txt}**"
        )


def render_structured_evidence(
    evidence: dict, msg_t: dict, route_info: dict, citations: list, sources: list
):
    """Layer 2: evidence (collapsed). Layer 3: debug (collapsed)."""
    if not evidence and not route_info and not citations:
        return

    sql = evidence.get("sql") or {} if evidence else {}

    assumptions = evidence.get("assumptions") or [] if evidence else []

    limitations = evidence.get("limitations") or [] if evidence else []

    verified_facts = evidence.get("verified_facts") or [] if evidence else []

    recommendations = evidence.get("recommendations") or [] if evidence else []

    ev_sources = evidence.get("sources") or [] if evidence else []

    has_evidence = bool(sql or ev_sources or verified_facts or recommendations)

    if has_evidence:

        with st.expander(msg_t["evidence_expander"], expanded=False):

            if sql:

                st.markdown(
                    f"**{msg_t['data_snapshot']}:** `{sql.get('data_snapshot', RATTI_DATA_SNAPSHOT)}`"
                )

                st.markdown(f"**{msg_t['metric']}:** `{sql.get('metric', 'n/a')}`")

                st.markdown(
                    f"**{msg_t['definition']}:** {sql.get('metric_definition', 'n/a')}"
                )

                st.markdown(
                    f"**{msg_t['time_range']}:** `{sql.get('time_range', 'n/a')}`"
                )

                st.markdown(
                    f"**{msg_t['rows']}:** `{sql.get('row_count', 0)}` · "
                    f"**{msg_t['sample_size']}:** `{sql.get('sample_size', 0)}`"
                )

                if sql.get("query"):

                    st.code(sql["query"], language="sql")

            for i, src in enumerate(ev_sources, start=1):

                st.markdown(
                    f"**[{i}] {src.get('source_name', 'Document')}** "
                    f"`{src.get('chunk_id', '')}`"
                )

            if verified_facts:

                st.markdown(f"**{msg_t['verified_facts']}**")

                for fact in verified_facts:

                    st.markdown(f"- {fact}")

            if recommendations:

                st.markdown(f"**{msg_t['recommendations']}**")

                for rec in recommendations:

                    st.markdown(f"- {rec}")

            if sql.get("formula"):

                st.markdown(f"**{msg_t['formula']}:** `{sql.get('formula')}`")

            if assumptions or limitations:

                if assumptions:

                    st.markdown(f"**{msg_t['assumptions']}**")

                    for item in assumptions:

                        st.markdown(f"- {item}")

                if limitations:

                    st.markdown(f"**{msg_t['limitations']}**")

                    for item in limitations:

                        st.markdown(f"- {item}")

    has_debug = bool(route_info or citations or sources)

    if has_debug:

        with st.expander(msg_t["debug_expander"], expanded=False):

            if route_info:

                st.markdown("**Router**")

                st.json(route_info)

            if citations:

                st.markdown("**Citations**")

                st.json(citations)

            if sources:

                st.markdown(f"**{msg_t['source_expander']}**")

                for i, src in enumerate(sources, start=1):

                    snippet = src.get("content", "")[:300]

                    source_name = src.get("source", "Policy Document")

                    st.markdown(f"**[{i}] {msg_t['source_label']}:** `{source_name}`")

                    if snippet:

                        st.markdown(f"> {snippet}")


# ---------------- Message Rendering ----------------

for msg in st.session_state.messages:

    role = msg["role"]

    content = msg["content"]

    intent = msg.get("intent")

    route_info = msg.get("route_info", {})

    sources = msg.get("sources", [])

    citations = msg.get("citations", [])

    evidence = msg.get("evidence", {})

    msg_lang = msg.get("lang", lang)

    msg_t = I18N[msg_lang]

    if role == "user":

        with st.chat_message("user"):

            st.markdown(content)

    else:

        with st.chat_message("assistant"):

            render_current_task(route_info or {"intent": intent}, msg_t, msg_lang)

            st.markdown(content)

            if msg.get("paused") or (route_info and route_info.get("paused")):

                st.warning(msg_t.get("paused_hitl", msg_t["human_approval_warning"]))

            elif route_info and route_info.get("human_approval_required"):

                st.warning(msg_t["human_approval_warning"])

            render_structured_evidence(evidence, msg_t, route_info, citations, sources)

if st.session_state.get("paused"):
    st.info(t.get("paused_hitl", t["human_approval_warning"]))
    hitl_note = st.text_input(t.get("hitl_note", "Note"), key="hitl_note")
    col_ok, col_no = st.columns(2)
    resume_choice = None
    if col_ok.button(t.get("approve", "Approve"), type="primary"):
        resume_choice = True
    if col_no.button(t.get("reject", "Reject")):
        resume_choice = False
    if resume_choice is not None:
        result = resume_thread(
            st.session_state.thread_id,
            approved=resume_choice,
            note=hitl_note,
            response_language=lang,
        )
        if result.get("thread_id"):
            st.session_state.thread_id = result["thread_id"]
            st.query_params["thread"] = result["thread_id"]
        st.session_state.paused = bool(result.get("paused"))
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result.get("answer"),
                "intent": result.get("intent"),
                "sources": result.get("sources") or [],
                "route_info": result.get("route_info") or {},
                "citations": result.get("citations") or [],
                "evidence": result.get("evidence") or {},
                "paused": bool(result.get("paused")),
                "interrupt": result.get("interrupt"),
                "lang": lang,
            }
        )
        st.rerun()

# ---------------- User Input ----------------

user_input = st.chat_input(t["chat_input"])

if st.session_state.get("paused") and user_input:

    user_input = None

if not user_input and st.session_state.get("pending_demo_question") and not st.session_state.get("paused"):

    user_input = st.session_state.pop("pending_demo_question")


def _run_copilot_ui(question: str, response_language: str):
    result = run_copilot(
        question,
        response_language,
        thread_id=st.session_state.get("thread_id"),
    )
    if result.get("thread_id"):
        st.session_state.thread_id = result["thread_id"]
        st.query_params["thread"] = result["thread_id"]
    st.session_state.paused = bool(result.get("paused"))
    return result


def _merge_clarification_reply(base_question: str, reply: str, lang_code: str) -> str:
    return merge_clarification_reply(base_question, reply, lang_code)


if user_input:

    st.session_state.messages.append(
        {"role": "user", "content": user_input, "lang": lang}
    )

    with st.chat_message("user"):

        st.markdown(user_input)

    base_q = st.session_state.clarification_base_question

    question_for_graph = (
        _merge_clarification_reply(base_q, user_input, lang) if base_q else user_input
    )

    with st.chat_message("assistant"):

        placeholder = st.empty()

        placeholder.markdown(t["analyzing"])

        result = _run_copilot_ui(
            question_for_graph, lang
        )

        answer = result["answer"]
        intent = result["intent"]
        sources = result["sources"]
        route_info = result["route_info"]
        citations = result["citations"]
        evidence = result["evidence"]
        paused = bool(result.get("paused"))

        time.sleep(0.2)

        placeholder.empty()

    if route_info.get("ambiguity_type"):

        st.session_state.clarification_base_question = question_for_graph

    else:

        st.session_state.clarification_base_question = None

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "intent": intent,
            "sources": sources,
            "route_info": route_info,
            "citations": citations,
            "evidence": evidence,
            "paused": paused,
            "interrupt": result.get("interrupt"),
            "lang": lang,
        }
    )

    st.rerun()
