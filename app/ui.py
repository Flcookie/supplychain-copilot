import sys, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import time

import streamlit as st

from core.demo_constants import RATTI_DATA_SNAPSHOT

st.markdown(
    "<style> .stChatMessage {font-size: 16px;} </style>", unsafe_allow_html=True
)

# Bump when graph / qualification behavior changes to bust Streamlit graph cache.

GRAPH_BUILD_VERSION = "ratti-lifecycle-v3-product"


def _graph_cache_key() -> str:
    """Invalidate cached graph when workflow/rules code changes."""

    root = os.path.dirname(os.path.dirname(__file__))

    watch_files = [
        os.path.join(root, "graph", "nodes.py"),
        os.path.join(root, "graph", "graph.py"),
        os.path.join(root, "core", "qualification_rules.py"),
        os.path.join(root, "core", "prompts.py"),
        os.path.join(root, "core", "router_overrides.py"),
        os.path.join(root, "core", "demo_constants.py"),
    ]

    mtimes = "|".join(
        str(os.path.getmtime(p)) for p in watch_files if os.path.exists(p)
    )

    return f"{GRAPH_BUILD_VERSION}|{mtimes}"


@st.cache_resource(show_spinner="Loading SupplyChain Copilot...")
def get_graph(_cache_key: str):

    from graph.graph import build_graph

    return build_graph()


graph = get_graph(_graph_cache_key())

DEMO_SCENARIOS = {
    "en": [
        ("— Select a scenario template —", ""),
        (
            "Supplier qualification checklist",
            "We have a new yarn supplier from China. What qualification process should we follow?",
        ),
        (
            "Yarn supplier KPIs (2025)",
            "Show the on-time delivery rate and defect rate of yarn suppliers in 2025.",
        ),
        (
            "High-risk supplier review",
            "Which suppliers should be reviewed this month due to high risk?",
        ),
        ("Vendor rating explanation", "Why did supplier SUP012 receive a C rating?"),
        (
            "Policy & ESG Q&A",
            "What ESG documents are required for yarn suppliers under Ratti qualification policy?",
        ),
        (
            "Complex question (policy + KPI)",
            "For strategic yarn suppliers, what monitoring policy applies and what was their average on-time delivery in 2025?",
        ),
    ],
    "zh": [
        ("— 选择场景模板 —", ""),
        ("供应商准入清单", "我们有一家来自中国的新纱线供应商，准入流程应该怎么走？"),
        (
            "纱线供应商 KPI（2025）",
            "Show the on-time delivery rate and defect rate of yarn suppliers in 2025.",
        ),
        (
            "高风险供应商复审",
            "Which suppliers should be reviewed this month due to high risk?",
        ),
        ("Vendor Rating 解释", "Why did supplier SUP012 receive a C rating?"),
        ("政策与 ESG 问答", "纱线供应商准入需要哪些 ESG 文件？"),
        (
            "复合问题（政策 + KPI）",
            "战略纱线供应商需要哪些监控政策？他们在 2025 年的平均准时交付率是多少？",
        ),
    ],
}

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

            if route_info and route_info.get("human_approval_required"):

                st.warning(msg_t["human_approval_warning"])

            render_structured_evidence(evidence, msg_t, route_info, citations, sources)

# ---------------- User Input ----------------

user_input = st.chat_input(t["chat_input"])

if not user_input and st.session_state.get("pending_demo_question"):

    user_input = st.session_state.pop("pending_demo_question")


def run_copilot(question: str, response_language: str):

    active_graph = get_graph(_graph_cache_key())

    result = active_graph.invoke(
        {"question": question, "response_language": response_language}
    )

    answer = result.get("answer", "No answer generated.")

    intent = result.get("intent", "policy_qa")

    sources = result.get("retrieved_docs", [])

    route_info = {
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "ambiguity_type": result.get("ambiguity_type"),
        "human_approval_required": result.get("human_approval_required"),
        "reason": result.get("reason"),
        "fallback_mode": result.get("fallback_mode", "none"),
        "kpi_parse": result.get("kpi_parse"),
    }

    citations = result.get("citations", [])

    evidence = result.get("evidence", {})

    return answer, intent, sources, route_info, citations, evidence


def _merge_clarification_reply(base_question: str, reply: str, lang_code: str) -> str:

    if lang_code == "zh":

        return f"{base_question.strip()}\n\n【用户补充】{reply.strip()}"

    return f"{base_question.strip()}\n\n[User clarification] {reply.strip()}"


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

        answer, intent, sources, route_info, citations, evidence = run_copilot(
            question_for_graph, lang
        )

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
            "lang": lang,
        }
    )

    st.rerun()
