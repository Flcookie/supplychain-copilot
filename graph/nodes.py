import json
from tools.sql_tools import run_sql_query
from core.prompts import KPI_SQL_PROMPT, KPI_ANSWER_PROMPT, SCENARIO_ANALYSIS_PROMPT

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from core.config import LLM_MODEL
from core.prompts import ROUTER_PROMPT, POLICY_QA_PROMPT
from rag.retriever import get_retriever
from .state import SCState

# Initialize LLM
llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=0,
)

retriever = get_retriever()


def router_node(state: SCState) -> SCState:
    """Determine the user's intent based on the question, with rule-based fallback to ensure KPI-related queries are not misclassified as policy questions."""
    q = state["question"]
    q_lower = q.lower()

    # Step 1️: Use LLM for initial intent prediction
    prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT)
    resp = llm.invoke(prompt.format(question=q))
    intent = resp.content.strip()

    # Step 2️: Rule-based fallback — prioritize KPI, Scenario, and Comparison queries

    # KPI keywords
    kpi_keywords_cn = ["准时交付率", "交付率", "交货率", "按时交付", "绩效", "KPI", "表现"]
    kpi_keywords_en = ["otd", "otif", "on-time", "on time", "performance", "kpi"]

    # Comparison keywords
    compare_keywords = ["compare", "vs", "versus", "对比", "比较"]

    # Supplier names (for auxiliary intent detection)
    supplier_keywords = ["Alpha", "Beta", "Gamma", "Delta"]

    # If KPI or comparison keywords appear, force to KPI node
    if (
        any(k in q_lower for k in kpi_keywords_en)
        or any(k in q for k in kpi_keywords_cn)
        or any(k in q_lower for k in compare_keywords)
    ):
        intent = "kpi_query"

    # If supplier names + performance-related words appear, also classify as KPI
    if any(s.lower() in q_lower for s in supplier_keywords) and (
        "率" in q or "表现" in q or "performance" in q_lower
    ):
        intent = "kpi_query"

    # If question contains “delay / risk / if”, classify as Scenario
    scenario_keywords = ["延迟", "delay", "晚到", "推迟", "断供", "中断", "风险", "impact"]
    if any(k in q for k in scenario_keywords) and "if" in q_lower or "如果" in q:
        intent = "scenario_analysis"

    # Default fallback to policy Q&A
    if intent not in ["policy_qa", "kpi_query", "scenario_analysis"]:
        intent = "policy_qa"

    # Save intent
    state["intent"] = intent
    return state



def policy_qa_node(state: SCState) -> SCState:
    """RAG: Retrieve supply chain policy/contract information from Pinecone and answer."""
    q = state["question"]

    docs = retriever.invoke(q)

    
    state["retrieved_docs"] = [
        {
            "content": d.page_content,
            "source": d.metadata.get("source", ""),
        }
        for d in docs
    ]

    context = "\n\n".join(d.page_content for d in docs)

    prompt = ChatPromptTemplate.from_template(POLICY_QA_PROMPT)
    resp = llm.invoke(prompt.format(question=q, context=context))

    state["answer"] = resp.content
    return state

def kpi_node(state: SCState) -> SCState:
    """Generate SQL based on user question, query the SQLite demo DB, and return KPI interpretation."""
    q = state["question"]

    # 1) Generate SQL using LLM
    prompt = ChatPromptTemplate.from_template(KPI_SQL_PROMPT)
    sql = llm.invoke(prompt.format(question=q)).content.strip()
    state["sql_query"] = sql

    # 2) Execute SQL
    try:
        rows = run_sql_query(sql)
    except Exception as e:
        state["answer"] = f"执行 KPI 查询时出错：{e}"
        state["sql_result"] = []
        return state

    state["sql_result"] = rows

    # 3) Let LLM explain the result in natural language
    explain_prompt = ChatPromptTemplate.from_template(KPI_ANSWER_PROMPT)
    resp = llm.invoke(
        explain_prompt.format(
            question=q,
            sql=sql,
            rows=json.dumps(rows, ensure_ascii=False),
        )
    )
    state["answer"] = resp.content
    return state

def scenario_node(state: SCState) -> SCState:
    """Parse simple delay scenarios and perform impact analysis based on sample data."""
    q = state["question"]

    # 1) Use LLM to extract parameters (country + delay days) from natural language
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
        scenario_spec = json.loads(parsed_raw)
    except Exception:
        scenario_spec = {"country": None, "delay_days": 7}

    state["scenario_spec"] = scenario_spec

    country = scenario_spec.get("country") or "VN" 

    # 2) Simplified: Query all orders in that country as “potentially affected orders”
    sql = f"""
    SELECT s.name AS supplier_name,
           s.country,
           COUNT(p.id) AS total_pos,
           SUM(p.qty) AS total_qty
    FROM suppliers s
    JOIN purchase_orders p ON s.id = p.supplier_id
    WHERE s.country = '{country}'
    GROUP BY s.id;
    """

    try:
        impact_rows = run_sql_query(sql)
    except Exception as e:
        impact_rows = [{"error": str(e)}]

    # 3) Let LLM generate structured risk analysis
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
    """Final output node: currently just returns the answer from the previous node; can be extended for formatting/tracing."""
    # Additional info (citations, internal traces, etc.) can be attached here later
    return state
