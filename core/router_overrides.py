"""Deterministic router overrides for Chinese and high-signal English lifecycle queries."""

from __future__ import annotations

import re
from typing import Any

_SUPPLIER_ID = re.compile(r"(SUP\d{3})", re.IGNORECASE)


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


def apply_lifecycle_router_overrides(parsed: dict[str, Any], question: str) -> dict[str, Any]:
    """Override LLM routing when lifecycle intent is unambiguous (esp. Chinese queries)."""
    q = question or ""
    lower = q.lower()
    parsed = _clear_coreference_when_supplier_named(parsed, q)

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

    return parsed


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
