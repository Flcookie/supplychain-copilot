import json
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from core.config import LLM_MODEL


KEYWORD_PROMPT = """Extract retrieval keywords from the supply-chain question.
Return strict JSON:
{{"suppliers": [], "metrics": [], "policy_terms": [], "countries": []}}

Question:
{question}
"""

HYDE_PROMPT = """Write a concise hypothetical answer that would contain the key facts needed to retrieve evidence.
Do not include unsupported numbers. Focus on supplier names, KPI terms, policy clauses, and risk terms.

Question:
{question}
"""


def extract_keywords(question: str) -> dict:
    heuristic = {
        "suppliers": re.findall(r"\b(?:Alpha Electronics|Beta Plastics|Gamma Metals|Delta Packaging)\b", question, re.I),
        "metrics": re.findall(r"\b(?:OTD|OTIF|on-time|defect|delay|risk score|order volume)\b", question, re.I),
        "policy_terms": re.findall(r"\b(?:policy|contract|clause|SOP|corrective action|backup supplier|scorecard)\b", question, re.I),
        "countries": re.findall(r"\b(?:Vietnam|China|Germany|VN|CN|DE)\b", question, re.I),
    }
    if any(heuristic.values()):
        return heuristic
    try:
        llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
        raw = llm.invoke(ChatPromptTemplate.from_template(KEYWORD_PROMPT).format(question=question)).content
        start = raw.find("{")
        end = raw.rfind("}")
        return json.loads(raw[start : end + 1])
    except Exception:
        return heuristic


def build_keyword_query(question: str) -> str:
    keywords = extract_keywords(question)
    tokens = []
    for values in keywords.values():
        tokens.extend(values)
    return " ".join(tokens) or question


def build_hyde_query(question: str) -> str:
    try:
        llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
        return llm.invoke(ChatPromptTemplate.from_template(HYDE_PROMPT).format(question=question)).content.strip()
    except Exception:
        return question
