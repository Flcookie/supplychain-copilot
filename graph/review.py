"""Review Agent: evidence gate + one-shot retrieval boost."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from core.evidence import document_evidence, hybrid_evidence
from core.llm import get_llm
from core.prompt_injection import prepare_retrieved_context, wrap_question_for_prompt
from rag.retriever import get_retriever

from .state import SCState

MAX_REVIEW_ATTEMPTS = 1

_STRONG_CLAIM = re.compile(
    r"\b(must|always|definitely|guaranteed|certainly|conclusively|"
    r"必须|一定|肯定|保证|毫无疑问)\b",
    re.IGNORECASE,
)

_EVIDENCE_INTENTS = {
    "policy_qa",
    "kpi_query",
    "hybrid_query",
    "risk_scenario",
    "vendor_rating_explanation",
    "supplier_assessment",
    "scenario_analysis",
}


def _is_zh(state: SCState) -> bool:
    return state.get("response_language", "en") == "zh"


def _has_document_evidence(state: SCState) -> bool:
    docs = state.get("retrieved_docs") or []
    if docs:
        return True
    citations = state.get("citations") or []
    if any(c.get("type") == "document" for c in citations if isinstance(c, dict)):
        return True
    evidence = state.get("evidence") or {}
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    return bool(sources)


def _has_sql_evidence(state: SCState) -> bool:
    if state.get("sql_result") is not None:
        return True
    if state.get("sql_query"):
        return True
    evidence = state.get("evidence") or {}
    if isinstance(evidence, dict) and evidence.get("sql"):
        return True
    citations = state.get("citations") or []
    return any(c.get("type") == "sql" for c in citations if isinstance(c, dict))


def _sql_row_count(state: SCState) -> int:
    rows = state.get("sql_result")
    if isinstance(rows, list):
        return len(rows)
    evidence = state.get("evidence") or {}
    if isinstance(evidence, dict):
        sql = evidence.get("sql") or {}
        if isinstance(sql, dict) and sql.get("row_count") is not None:
            return int(sql["row_count"])
    return 0


def _evidence_gaps(state: SCState) -> list[str]:
    intent = state.get("intent") or "policy_qa"
    answer = (state.get("answer") or "").strip()
    gaps: list[str] = []

    if not answer:
        gaps.append("empty_answer")
        return gaps

    if intent not in _EVIDENCE_INTENTS:
        return gaps

    has_docs = _has_document_evidence(state)
    has_sql = _has_sql_evidence(state)

    if intent == "policy_qa" and not has_docs:
        gaps.append("missing_policy_citations")
    elif intent == "kpi_query" and not has_sql:
        gaps.append("missing_sql_result")
    elif intent in {"risk_scenario", "scenario_analysis", "vendor_rating_explanation"} and not (
        has_sql or has_docs
    ):
        gaps.append("missing_risk_or_rating_evidence")
    elif intent == "hybrid_query" and not (has_docs and has_sql):
        if not has_docs:
            gaps.append("missing_policy_citations")
        if not has_sql:
            gaps.append("missing_sql_result")
    elif intent == "supplier_assessment":
        profile = state.get("assessment_profile") or {}
        if not profile.get("rows") and not has_sql:
            gaps.append("missing_supplier_profile")
        if not has_docs and not state.get("assessment_policy_docs"):
            gaps.append("missing_policy_citations")
        kpi = state.get("assessment_kpi") or {}
        if not kpi.get("rows") and _sql_row_count(state) == 0:
            gaps.append("missing_kpi_snapshot")

    if has_sql and _sql_row_count(state) == 0 and intent in {
        "kpi_query",
        "vendor_rating_explanation",
        "supplier_assessment",
    }:
        # Zero rows is still evidence (negative result) — flag as soft limitation only.
        gaps.append("empty_sql_result")

    if _STRONG_CLAIM.search(answer) and not has_docs and not has_sql:
        gaps.append("unsupported_strong_claims")

    return gaps


def _append_limitation(answer: str, gaps: list[str], *, zh: bool) -> str:
    soft_only = gaps == ["empty_sql_result"]
    if zh:
        if soft_only:
            note = (
                "\n\n---\n**审核备注：** SQL 查询已执行但返回 0 行；"
                "结论已按「无匹配记录」表述，请勿过度外推。"
            )
        else:
            note = (
                "\n\n---\n**审核拦截：** 部分结论缺少可核对的政策引用或 SQL 证据"
                f"（{', '.join(gaps)}）。以上内容仅供决策参考，"
                "证据不足处已降级为不确定表述，请人工复核后再行动。"
            )
    else:
        if soft_only:
            note = (
                "\n\n---\n**Review note:** SQL ran but returned 0 rows; "
                "treat the conclusion as 'no matching records' and avoid over-generalizing."
            )
        else:
            note = (
                "\n\n---\n**Review gate:** Some claims lack verifiable policy citations or SQL evidence "
                f"({', '.join(gaps)}). Treat the answer as decision support only; "
                "underspecified points were softened — confirm with a buyer before acting."
            )
    if note.strip() in answer:
        return answer
    return answer.rstrip() + note


def _llm_review_notes(state: SCState, gaps: list[str]) -> dict[str, Any]:
    """Optional LLM assist — never the sole gate; failures fall back to rule gaps."""
    try:
        prompt = ChatPromptTemplate.from_template(REVIEW_PROMPT)
        evidence = state.get("evidence") or {}
        resp = get_llm().invoke(
            prompt.format(
                question=state.get("question", ""),
                answer=state.get("answer", ""),
                intent=state.get("intent", ""),
                evidence_summary=json.dumps(
                    {
                        "gaps_rule": gaps,
                        "has_docs": _has_document_evidence(state),
                        "has_sql": _has_sql_evidence(state),
                        "sql_rows": _sql_row_count(state),
                        "evidence_type": evidence.get("evidence_type")
                        if isinstance(evidence, dict)
                        else None,
                        "citation_count": len(state.get("citations") or []),
                    },
                    ensure_ascii=False,
                ),
            )
        )
        text = (resp.content or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except Exception:
        return {
            "passed": not gaps or gaps == ["empty_sql_result"],
            "unsupported_claims": [],
            "notes": "rule-based review only",
        }


def review_node(state: SCState) -> SCState:
    """Check that the draft answer is backed by retrieval/SQL evidence."""
    attempts = int(state.get("review_attempts") or 0)

    if state.get("injection_blocked") or state.get("ambiguity_type"):
        state["review_status"] = "skipped"
        state["review_notes"] = "skipped_clarification_or_injection"
        return state

    if not (state.get("answer") or "").strip():
        state["review_status"] = "failed"
        state["review_notes"] = "empty_answer"
        state["unsupported_claims"] = ["empty_answer"]
        return state

    gaps = _evidence_gaps(state)
    # Soft gap: empty SQL is informational — do not fail/boost.
    hard_gaps = [g for g in gaps if g != "empty_sql_result"]
    boostable = any(
        g
        in {
            "missing_policy_citations",
            "missing_supplier_profile",
            "missing_kpi_snapshot",
            "unsupported_strong_claims",
        }
        for g in hard_gaps
    ) and state.get("intent") in {
        "policy_qa",
        "hybrid_query",
        "supplier_assessment",
        "rag_fallback",
    }

    llm_result = _llm_review_notes(state, gaps)
    unsupported = list(llm_result.get("unsupported_claims") or [])
    if hard_gaps and not unsupported:
        unsupported = hard_gaps

    if hard_gaps and boostable and attempts < MAX_REVIEW_ATTEMPTS:
        state["review_status"] = "needs_more_evidence"
        state["review_attempts"] = attempts + 1
        state["review_notes"] = llm_result.get("notes") or f"boost for: {', '.join(hard_gaps)}"
        state["unsupported_claims"] = unsupported
        return state

    zh = _is_zh(state)
    if hard_gaps:
        state["answer"] = _append_limitation(state.get("answer") or "", hard_gaps, zh=zh)
        state["review_status"] = "failed"
        state["review_notes"] = llm_result.get("notes") or f"gated: {', '.join(hard_gaps)}"
        state["unsupported_claims"] = unsupported
    else:
        if gaps:  # soft empty_sql_result
            state["answer"] = _append_limitation(state.get("answer") or "", gaps, zh=zh)
        state["review_status"] = "passed"
        state["review_notes"] = llm_result.get("notes") or "evidence checks passed"
        state["unsupported_claims"] = unsupported
    return state


def evidence_boost_node(state: SCState) -> SCState:
    """One-shot wider retrieval then light regeneration for policy-heavy answers."""
    q = state.get("question") or ""
    intent = state.get("intent") or "policy_qa"
    zh = _is_zh(state)

    wide = get_retriever(k=8, doc_types=["policy", "contract", "sop", "faq", "kpi_dict"])
    docs = wide.invoke(q)
    state["retrieved_docs"] = [
        {
            "content": d.page_content,
            "source": d.metadata.get("source_name") or d.metadata.get("source", ""),
        }
        for d in docs
    ]
    if intent == "supplier_assessment":
        state["assessment_policy_docs"] = state["retrieved_docs"]

    citations = []
    for i, doc in enumerate(docs, start=1):
        citations.append(
            {
                "type": "document",
                "source": doc.metadata.get("source_name") or doc.metadata.get("source", ""),
                "chunk_id": doc.metadata.get("chunk_id") or f"boost-{i}",
                "clause": doc.metadata.get("section_title") or doc.metadata.get("section", ""),
                "doc_type": doc.metadata.get("doc_type", ""),
                "retrieval_score": doc.metadata.get("retrieval_score"),
                "boosted": True,
            }
        )
    prior = [c for c in (state.get("citations") or []) if isinstance(c, dict)]
    state["citations"] = prior + citations

    if intent in {"policy_qa", "hybrid_query", "supplier_assessment"} and docs:
        prepared = prepare_retrieved_context(docs)
        docs = prepared["kept"] or docs
        lang_instruction = (
            "请用中文回答。" if zh else "Answer in English."
        )
        prior_answer = state.get("answer") or ""
        prompt = ChatPromptTemplate.from_template(POLICY_QA_PROMPT)
        # Reuse policy QA template with boosted context; keep prior draft as hint in question.
        boosted_q = (
            f"{q}\n\n[Reviewer note: previous draft lacked citations. "
            f"Regenerate with explicit evidence. Prior draft:\n{prior_answer[:800]}]"
        )
        resp = get_llm().invoke(
            prompt.format(
                question=wrap_question_for_prompt(boosted_q),
                context=prepared["context"],
                response_language_instruction=lang_instruction,
            )
        )
        state["answer"] = resp.content

    if state.get("sql_result") is not None or (state.get("evidence") or {}).get("sql"):
        sql_ev = (state.get("evidence") or {}).get("sql") if isinstance(state.get("evidence"), dict) else None
        state["evidence"] = hybrid_evidence(
            docs=docs,
            sql=sql_ev,
            sample_size=(state.get("evidence") or {}).get("sample_size")
            if isinstance(state.get("evidence"), dict)
            else None,
            minimum_sample_size=1,
            limitations=["Answer regenerated after evidence-boost review pass."],
        )
    else:
        state["evidence"] = document_evidence(
            docs,
            evidence_type="document",
            limitations=["Answer regenerated after evidence-boost review pass."],
        )

    state["task_step"] = "evidence_boost"
    return state
