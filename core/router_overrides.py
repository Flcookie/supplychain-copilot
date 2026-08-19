"""Deterministic router overrides for Chinese and high-signal English lifecycle queries.

Monitor feedback loop (not auto-tuning):
  When observability/metrics.py shows an intent's mean confidence dropping or
  clarification/HITL rates spiking, export traces with
  `python -m eval.badcase_export`, label them, then add or tighten a rule below.
  Tag the change with `# tuned from badcase batch YYYY-MM-DD`.
"""

from __future__ import annotations

import re
from typing import Any

_SUPPLIER_ID = re.compile(r"(SUP\d{3})", re.IGNORECASE)
_PRONOUN_RE = re.compile(r"\b(they|their|them|those)\b", re.IGNORECASE)

# Dump / exfil-adjacent phrasing. Safety gate — not an intent-override for misses.
_OVERBROAD_PHRASES_EN = (
    "show me all data",
    "all data about",
    "entire dataset",
    "entire database",
    "dump the database",
    "dump all data",
    "dump all",
    "export all",
    "export every",
    "export the entire",
    "all records",
    "every record",
)
_OVERBROAD_PHRASES_ZH = (
    "全部数据",
    "所有数据",
    "导出所有",
    "导出全部",
    "全部供应商",
    "所有供应商的数据",
)

# Category / group NPs that can bind they/them/他们 in the same question.
_ANTECEDENT_ZH = ("纱线", "面料", "拉链", "包装", "化工", "外发", "战略")
_ANTECEDENT_EN = ("yarn", "fabric", "chemical", "packaging", "zipper", "outsourced")


def _has_supplier_id(question: str) -> bool:
    return _SUPPLIER_ID.search(question or "") is not None


def _extract_supplier_id(question: str) -> str | None:
    match = _SUPPLIER_ID.search(question or "")
    return match.group(1).upper() if match else None


def _clear_coreference_when_supplier_named(parsed: dict[str, Any], question: str) -> dict[str, Any]:
    """Workbench rows already identify a supplier — do not ask which one."""
    if not _has_supplier_id(question):
        return parsed
    if parsed.get("ambiguity_type") != "coreference":
        return parsed
    out = dict(parsed)
    out["ambiguity_type"] = None
    if float(out.get("confidence", 0)) < 0.78:
        out["confidence"] = 0.85
    out["reason"] = f"{out.get('reason', '')} (supplier id in query — skip coreference)".strip()
    return out


def is_overbroad_data_request(question: str) -> bool:
    """True when the user asks to dump the full supplier dataset (clarification/refuse)."""
    q = question or ""
    lower = q.lower()
    if any(phrase in lower for phrase in _OVERBROAD_PHRASES_EN):
        return True
    return any(phrase in q for phrase in _OVERBROAD_PHRASES_ZH)


def _has_named_group_antecedent(question: str) -> bool:
    """Pronouns are bound if the same question already names a category or supplier group."""
    q = question or ""
    lower = q.lower()
    if any(token in q for token in _ANTECEDENT_ZH):
        return True
    if any(re.search(rf"\b{re.escape(token)}\b", lower) for token in _ANTECEDENT_EN):
        return True
    return re.search(r"\bsuppliers\b", lower) is not None


def is_unresolved_coreference(question: str) -> bool:
    """True when they/them/这家 have no supplier id and no in-sentence group antecedent."""
    q = question or ""
    if _has_supplier_id(q):
        return False
    lower = q.lower()
    if any(
        phrase in lower
        for phrase in ("this supplier", "those vendors", "supplier a and supplier b")
    ):
        return True
    if "这家" in q or "那个供应商" in q:
        return True
    if "他们" in q:
        return not _has_named_group_antecedent(q)
    if _PRONOUN_RE.search(lower):
        return not _has_named_group_antecedent(q)
    return False


def _apply_overbroad_gate(parsed: dict[str, Any], question: str) -> dict[str, Any] | None:
    if not is_overbroad_data_request(question):
        return None
    out = dict(parsed)
    out["intent"] = "policy_qa"
    out["ambiguity_type"] = "overbroad_data_request"
    out["confidence"] = min(float(out.get("confidence") or 0.7), 0.7)
    out["reason"] = "overbroad data request (safety gate)"
    return out


def _apply_coreference_gate(parsed: dict[str, Any], question: str) -> dict[str, Any]:
    if parsed.get("ambiguity_type") in {
        "overbroad_data_request",
        "missing_entity",
        "composite_intent",
    }:
        return parsed
    if parsed.get("intent") == "qualification_checklist":
        return parsed
    from core.qualification_rules import detect_qualification_checklist_intent

    if detect_qualification_checklist_intent(question):
        return parsed
    if not is_unresolved_coreference(question):
        return parsed
    out = dict(parsed)
    out["ambiguity_type"] = "coreference"
    out["confidence"] = min(float(out.get("confidence") or 0.8), 0.8)
    out["reason"] = f"{out.get('reason', '')} (coreference gate)".strip()
    return out


def apply_lifecycle_router_overrides(parsed: dict[str, Any], question: str) -> dict[str, Any]:
    """Override LLM routing when lifecycle intent is unambiguous (esp. Chinese queries)."""
    q = question or ""
    lower = q.lower()
    parsed = _clear_coreference_when_supplier_named(parsed, q)

    overbroad = _apply_overbroad_gate(parsed, q)
    if overbroad is not None:
        return overbroad

    # Full supplier assessment task (before narrower rating/KPI overrides)
    assessment_signal = any(
        phrase in lower
        for phrase in [
            "full assessment",
            "full supplier assessment",
            "supplier assessment",
            "assess supplier",
            "evaluate supplier",
            "assessment report",
            "risk assessment summary",
            "supplier evaluation report",
        ]
    ) or any(
        phrase in q
        for phrase in [
            "完整评估",
            "供应商评估",
            "评估报告",
            "评估供应商",
            "全面评估",
            "风险评估摘要",
        ]
    )
    if assessment_signal:
        if _has_supplier_id(q):
            return _set_intent(
                parsed,
                "supplier_assessment",
                0.97,
                "supplier assessment task (rule override)",
            )
        out = _set_intent(
            parsed,
            "supplier_assessment",
            0.7,
            "supplier assessment needs supplier id",
        )
        out["ambiguity_type"] = "missing_entity"
        return out

    # Vendor rating explanation (incl. Chinese)
    rating_ask = (
        any(
            token in q
            for token in [
                "C级评级",
                "C 级评级",
                "B级评级",
                "A级评级",
                "D级评级",
                "级评级",
                "vendor rating",
                "rating class",
            ]
        )
        or ("获得了" in q and "级" in q and "评级" in q)
        or re.search(r"receiv(e|ed) a [a-d] rating", lower)
        or re.search(r"\b[a-d]\s*rating\b", lower)
    )
    if _has_supplier_id(q) and (
        rating_ask
        or re.search(r"\b[a-d]\s*rating\b", lower)
        or re.search(r"receiv(e|ed) a [a-d] rating", lower)
        or "获得了" in q and "级" in q
    ):
        return _set_intent(parsed, "vendor_rating_explanation", 0.95, "vendor rating explanation (rule override)")

    if ("vendor rating formula" in lower or "评级公式" in q or "评分公式" in q) and (
        "yarn" in lower or "纱线" in q
    ):
        return _set_intent(parsed, "vendor_rating_explanation", 0.93, "rating formula explanation (rule override)")

    if "qualified with reserve" in lower or ("qualified" in lower and "reserve" in lower):
        return _set_intent(
            parsed,
            "vendor_rating_explanation",
            0.91,
            "reserve candidate recommendation (rule override)",
            human_approval=True,
        )

    # Risk scenario (incl. Chinese)
    if any(
        phrase in q
        for phrase in [
            "本月应审查",
            "本月需要审查",
            "本月审查",
            "这个月应审查",
            "高风险",
            "风险较高",
            "单源",
            "单一来源",
            "黑名单",
        ]
    ) or ("review" in lower and "this month" in lower and "risk" in lower):
        human = "blacklist" in lower or "黑名单" in q
        return _set_intent(
            parsed,
            "risk_scenario",
            0.94,
            "risk scenario (rule override)",
            human_approval=human,
        )

    if _extract_supplier_id(q) and any(
        token in q for token in ["质量问题", "质量异常", "quality issues", "quality issue", "重复质量"]
    ):
        return _set_intent(parsed, "risk_scenario", 0.93, "supplier quality risk (rule override)")

    if ("delayed" in lower or "延迟" in q) and any(
        token in q for token in ["what should", "buyer check", "买家", "采购员", "应该检查"]
    ):
        return _set_intent(parsed, "risk_scenario", 0.92, "what-if delay risk (rule override)")

    # Hybrid: policy + KPI in the same question (must run before yarn KPI override)
    policy_signal = any(
        token in q
        for token in [
            "监控政策",
            "政策",
            "monitoring policy",
            "monitoring policies",
            "what policy",
            "which policy",
            "ESG文件",
            "esg document",
            "esg documents",
        ]
    ) or ("policy" in lower and ("applies" in lower or "required" in lower or "need" in lower))
    kpi_signal = any(
        token in q
        for token in [
            "准时交付",
            "交付率",
            "缺陷率",
            "平均准时",
            "on-time",
            "on time delivery",
            "defect rate",
            "otd",
            "平均交付",
        ]
    )
    if policy_signal and kpi_signal:
        return _set_intent(parsed, "hybrid_query", 0.95, "policy + KPI composite (rule override)")

    # KPI: yarn OTD + defect (Chinese)
    if ("纱线" in q or "yarn" in lower) and kpi_signal:
        return _set_intent(parsed, "kpi_query", 0.94, "yarn KPI query (rule override)")

    return _apply_coreference_gate(parsed, q)


def _set_intent(
    parsed: dict[str, Any],
    intent: str,
    confidence: float,
    reason: str,
    human_approval: bool = False,
) -> dict[str, Any]:
    out = dict(parsed)
    out["intent"] = intent
    out["confidence"] = max(float(parsed.get("confidence", 0)), confidence)
    out["ambiguity_type"] = None
    out["reason"] = reason
    if human_approval:
        out["human_approval_required"] = True
    return out
