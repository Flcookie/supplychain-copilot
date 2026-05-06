import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import time
import streamlit as st
from core.config import LLM_MODEL, EMBEDDING_MODEL, PINECONE_INDEX_NAME
from graph.graph import build_graph

st.markdown("<style> .stChatMessage {font-size: 16px;} </style>", unsafe_allow_html=True)


# Initialize graph
graph = build_graph()

I18N = {
    "en": {
        "sidebar_title": "### 🏢 SupplyChain Copilot",
        "sidebar_desc": """
        An **AI assistant for enterprise supply chain management**, powered by LangGraph and RAG.

        **Capabilities:**
        - 📘 Policy Q&A via RAG (retrieval from policy/contract documents)
        - 📊 KPI Query via SQL over demo database
        - ⚙️ Scenario analysis for supplier delays or risks
        """,
        "system_info": "**System Info**",
        "try_asking": "💡 Try asking:\n- What is our on-time delivery rate for Alpha Electronics?\n- How do we define strategic suppliers?\n- What happens if Vietnam suppliers are delayed by 7 days?",
        "title_desc": "AI Copilot for Supplier Performance & Policy Intelligence · Built with LangGraph + Pinecone + Streamlit",
        "source_expander": "📎 View Referenced Documents",
        "route_expander": "🧭 Route Decision",
        "evidence_expander": "🧾 Execution Evidence",
        "source_label": "Source",
        "chat_input": "Ask a question about suppliers, KPIs, or risk scenarios...",
        "analyzing": "Analyzing your question... please wait.",
        "copilot": "**Copilot**",
        "language_label": "Language",
    },
    "zh": {
        "sidebar_title": "### 🏢 供应链 Copilot",
        "sidebar_desc": """
        一个面向企业供应链场景的 **AI 助手**，基于 LangGraph 与 RAG。

        **能力：**
        - 📘 政策问答（RAG 文档检索）
        - 📊 KPI 查询（自然语言转 SQL）
        - ⚙️ 风险推演（延迟/中断情景分析）
        """,
        "system_info": "**系统信息**",
        "try_asking": "💡 你可以试试：\n- Alpha Electronics 的准时交付率是多少？\n- 战略供应商如何定义？\n- 如果越南供应商延迟 7 天会有什么影响？",
        "title_desc": "面向供应商绩效与政策智能的 AI Copilot · 基于 LangGraph + Pinecone + Streamlit",
        "source_expander": "📎 查看引用文档",
        "route_expander": "🧭 路由决策",
        "evidence_expander": "🧾 执行证据",
        "source_label": "来源",
        "chat_input": "请输入供应商、KPI 或风险相关问题...",
        "analyzing": "正在分析你的问题，请稍候...",
        "copilot": "**Copilot**",
        "language_label": "语言",
    },
}

# ---------------- Streamlit Config ----------------
st.set_page_config(
    page_title="SupplyChain Copilot",
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
    st.markdown(t["system_info"])
    st.markdown(f"- LLM: `{LLM_MODEL}`")
    st.markdown(f"- Embedding: `{EMBEDDING_MODEL}`")
    st.markdown(f"- Vector Index: `{PINECONE_INDEX_NAME}`")
    st.markdown("---")
    st.caption(t["try_asking"])

# ---------------- Session State ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []
# When router sends user to clarification, we merge follow-up replies with this base question.
if "clarification_base_question" not in st.session_state:
    st.session_state.clarification_base_question = None

# ---------------- Title ----------------
st.markdown(
    f"""
    <div style="padding: 0 0 8px 0;">
        <h1 style="margin-bottom: 0; font-size: 30px;">SupplyChain Copilot</h1>
        <p style="color: #666; margin-top: 4px; font-size: 14px;">
            {t["title_desc"]}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------- Intent Badge ----------------
def intent_badge(intent: str, lang_code: str = "en") -> str:
    intent = (intent or "policy_qa").lower()
    labels = {
        "en": {"policy_qa": "Policy Q&A", "kpi_query": "KPI Query", "scenario_analysis": "Scenario", "general": "General"},
        "zh": {"policy_qa": "政策问答", "kpi_query": "KPI 查询", "scenario_analysis": "风险推演", "general": "通用"},
    }
    lang_labels = labels.get(lang_code, labels["en"])
    if intent == "policy_qa":
        label, color = lang_labels["policy_qa"], "#0f766e"
    elif intent == "kpi_query":
        label, color = lang_labels["kpi_query"], "#2563eb"
    elif intent == "scenario_analysis":
        label, color = lang_labels["scenario_analysis"], "#ea580c"
    else:
        label, color = lang_labels["general"], "#6b7280"

    return f"""
    <span style="
        display:inline-block;
        padding:2px 8px;
        margin-left:6px;
        border-radius:999px;
        background:{color}15;
        color:{color};
        font-size:10px;
        border:1px solid {color}40;
        vertical-align:middle;
    ">{label}</span>
    """

# ---------------- Message Rendering ----------------
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    intent = msg.get("intent")
    route_info = msg.get("route_info", {})
    sources = msg.get("sources", [])
    citations = msg.get("citations", [])
    msg_lang = msg.get("lang", lang)
    msg_t = I18N[msg_lang]

    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message("assistant"):
            if intent:
                st.markdown(f"{msg_t['copilot']} {intent_badge(intent, msg_lang)}", unsafe_allow_html=True)
            else:
                st.markdown(msg_t["copilot"])
            st.markdown(content)
            if route_info:
                with st.expander(msg_t["route_expander"]):
                    st.json(route_info)
            if sources:
                with st.expander(msg_t["source_expander"]):
                    for i, src in enumerate(sources, start=1):
                        snippet = src.get("content", "")[:300]
                        source_name = src.get("source", "Policy Document")
                        st.markdown(f"**[{i}] {msg_t['source_label']}:** `{source_name}`")
                        if snippet:
                            st.markdown(f"> {snippet}")
                        st.markdown("---")
            if citations:
                with st.expander(msg_t["evidence_expander"]):
                    st.json(citations)

# ---------------- User Input ----------------
user_input = st.chat_input(t["chat_input"])

def run_copilot(question: str, response_language: str):
    result = graph.invoke({"question": question, "response_language": response_language})
    answer = result.get("answer", "No answer generated.")
    intent = result.get("intent", "policy_qa")
    sources = result.get("retrieved_docs", [])
    route_info = {
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "ambiguity_type": result.get("ambiguity_type"),
        "reason": result.get("reason"),
        "fallback_mode": result.get("fallback_mode", "none"),
        "kpi_parse": result.get("kpi_parse"),
    }
    citations = result.get("citations", [])
    return answer, intent, sources, route_info, citations

def _merge_clarification_reply(base_question: str, reply: str, lang_code: str) -> str:
    if lang_code == "zh":
        return f"{base_question.strip()}\n\n【用户补充】{reply.strip()}"
    return f"{base_question.strip()}\n\n[User clarification] {reply.strip()}"


if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input, "lang": lang})
    with st.chat_message("user"):
        st.markdown(user_input)

    base_q = st.session_state.clarification_base_question
    question_for_graph = (
        _merge_clarification_reply(base_q, user_input, lang) if base_q else user_input
    )

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown(t["analyzing"])
        answer, intent, sources, route_info, citations = run_copilot(question_for_graph, lang)
        time.sleep(0.2)
        placeholder.empty()

    # Multi-turn clarification: accumulate context until ambiguity_type is cleared.
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
            "lang": lang,
        }
    )
    # Ensure the new assistant turn is rendered only once via the history loop.
    st.rerun()
