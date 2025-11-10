import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import time
import streamlit as st
from core.config import LLM_MODEL, EMBEDDING_MODEL, PINECONE_INDEX_NAME
from graph.graph import build_graph

st.markdown("<style> .stChatMessage {font-size: 16px;} </style>", unsafe_allow_html=True)


# Initialize graph
graph = build_graph()

# ---------------- Streamlit Config ----------------
st.set_page_config(
    page_title="SupplyChain Copilot",
    page_icon="🟢",
    layout="wide",
)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### 🏢 SupplyChain Copilot")
    st.markdown(
        """
        An **AI assistant for enterprise supply chain management**, powered by LangGraph and RAG.

        **Capabilities:**
        - 📘 Policy Q&A via RAG (retrieval from policy/contract documents)
        - 📊 KPI Query via SQL over demo database
        - ⚙️ Scenario analysis for supplier delays or risks
        """
    )
    st.markdown("---")
    st.markdown("**System Info**")
    st.markdown(f"- LLM: `{LLM_MODEL}`")
    st.markdown(f"- Embedding: `{EMBEDDING_MODEL}`")
    st.markdown(f"- Vector Index: `{PINECONE_INDEX_NAME}`")
    st.markdown("---")
    st.caption("💡 Try asking:\n- What is our on-time delivery rate for Alpha Electronics?\n- How do we define strategic suppliers?\n- What happens if Vietnam suppliers are delayed by 7 days?")

# ---------------- Session State ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- Title ----------------
st.markdown(
    """
    <div style="padding: 0 0 8px 0;">
        <h1 style="margin-bottom: 0; font-size: 30px;">SupplyChain Copilot</h1>
        <p style="color: #666; margin-top: 4px; font-size: 14px;">
            AI Copilot for Supplier Performance & Policy Intelligence · Built with LangGraph + Pinecone + Streamlit
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------- Intent Badge ----------------
def intent_badge(intent: str) -> str:
    intent = (intent or "policy_qa").lower()
    if intent == "policy_qa":
        label, color = "Policy Q&A", "#0f766e"
    elif intent == "kpi_query":
        label, color = "KPI Query", "#2563eb"
    elif intent == "scenario_analysis":
        label, color = "Scenario", "#ea580c"
    else:
        label, color = "General", "#6b7280"

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
    sources = msg.get("sources", [])

    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message("assistant"):
            if intent:
                st.markdown(f"**Copilot** {intent_badge(intent)}", unsafe_allow_html=True)
            else:
                st.markdown("**Copilot**")
            st.markdown(content)
            if sources:
                with st.expander("📎 View Referenced Documents"):
                    for i, src in enumerate(sources, start=1):
                        snippet = src.get("content", "")[:300]
                        source_name = src.get("source", "Policy Document")
                        st.markdown(f"**[{i}] Source:** `{source_name}`")
                        if snippet:
                            st.markdown(f"> {snippet}")
                        st.markdown("---")

# ---------------- User Input ----------------
user_input = st.chat_input("Ask a question about suppliers, KPIs, or risk scenarios...")

def run_copilot(question: str):
    result = graph.invoke({"question": question})
    answer = result.get("answer", "No answer generated.")
    intent = result.get("intent", "policy_qa")
    sources = result.get("retrieved_docs", [])
    return answer, intent, sources

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("Analyzing your question... please wait.")
        answer, intent, sources = run_copilot(user_input)
        time.sleep(0.2)
        placeholder.empty()
        st.markdown(f"**Copilot** {intent_badge(intent)}", unsafe_allow_html=True)
        st.markdown(answer)
        if sources:
            with st.expander("📎 View Referenced Documents"):
                for i, src in enumerate(sources, start=1):
                    snippet = src.get("content", "")[:300]
                    source_name = src.get("source", "Policy Document")
                    st.markdown(f"**[{i}] Source:** `{source_name}`")
                    if snippet:
                        st.markdown(f"> {snippet}")
                    st.markdown("---")

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "intent": intent, "sources": sources}
    )
