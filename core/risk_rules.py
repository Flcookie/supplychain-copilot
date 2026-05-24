"""Lightweight risk signal → recommended action mapping for Ratti demo."""

from __future__ import annotations

RISK_LEVEL_ACTIONS: dict[str, str] = {
    "High": "Schedule ad-hoc review; escalate to procurement manager.",
    "Medium": "Monitor closely; confirm mitigation plan with buyer.",
    "Low": "Continue regular monitoring per Kraljic cadence.",
}

EVENT_TYPE_ACTIONS: dict[str, str] = {
    "Quality": "Request corrective action plan; consider audit for strategic suppliers.",
    "Delivery": "Review safety stock and alternate qualified suppliers.",
    "Financial": "Request updated financial statements; escalate if strategic.",
    "Geopolitical": "Assess supply continuity; review backup sourcing.",
    "Compliance": "Validate documents; hold status change until evidence received.",
    "Single Sourcing": "Scout backup supplier; document contingency plan.",
}

QUALITY_SEVERITY_ACTIONS: dict[str, str] = {
    "Critical": "Immediate corrective action; ad-hoc audit recommended.",
    "Major": "Corrective action required; buyer confirmation before next PO.",
    "Minor": "Track trend; request improvement plan if repeated.",
}


def action_for_risk_level(risk_level: str | None) -> str:
    if not risk_level:
        return "Review supplier risk profile with buyer."
    return RISK_LEVEL_ACTIONS.get(risk_level, "Review supplier risk profile with buyer.")


def action_for_event_type(event_type: str | None) -> str:
    if not event_type:
        return "Review open risk events and confirm mitigation owner."
    for key, action in EVENT_TYPE_ACTIONS.items():
        if key.lower() in (event_type or "").lower():
            return action
    return "Review open risk events and confirm mitigation owner."


def action_for_quality_severity(severity: str | None) -> str:
    if not severity:
        return "Review quality events and agree corrective actions with supplier."
    return QUALITY_SEVERITY_ACTIONS.get(severity, "Review quality events and agree corrective actions.")


def single_sourcing_guidance() -> list[str]:
    return [
        "Single sourcing increases disruption and traceability risk for strategic categories.",
        "Scout at least one qualified backup supplier in the same category.",
        "Validate subcontracting transparency and safety stock coverage.",
        "For outsourced fabric/yarn processing, confirm chemical finishing compliance and audit trail.",
    ]


def blacklist_guidance() -> list[str]:
    return [
        "AI can summarize risk evidence but cannot approve blacklisting autonomously.",
        "Procurement manager must review financial, quality, compliance and strategic impact.",
        "Document rationale and obtain legal/compliance sign-off before status change.",
    ]
