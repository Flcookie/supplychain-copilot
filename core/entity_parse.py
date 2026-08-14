"""Lightweight parsers used by graph nodes and tests (no LLM / vectorstore)."""

from __future__ import annotations

import re

_SUPPLIER_ID_PATTERN = re.compile(r"(SUP\d{3})", re.IGNORECASE)


def extract_supplier_id(text: str) -> str | None:
    match = _SUPPLIER_ID_PATTERN.search(text or "")
    return match.group(1).upper() if match else None


def classify_risk_question(question: str) -> str:
    q = (question or "").lower()
    raw = question or ""
    if "blacklist" in q or "黑名单" in raw:
        return "blacklist"
    if (
        "single sourcing" in q
        or "single-sourcing" in q
        or "single source" in q
        or "单源" in raw
        or "单一来源" in raw
    ):
        return "single_sourcing"
    if any(
        phrase in raw
        for phrase in [
            "review this month",
            "reviewed this month",
            "本月应审查",
            "本月需要审查",
            "本月审查",
            "这个月应审查",
            "due to high risk",
            "高风险",
            "风险较高",
        ]
    ) or ("review" in q and "high risk" in q):
        return "review_due"
    if extract_supplier_id(question) and ("quality" in q or "issues" in q):
        return "quality_issues"
    return "what_if_delay"
