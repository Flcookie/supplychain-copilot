"""Ratti supplier qualification rules and checklist generator."""

from __future__ import annotations

import re
from typing import Any

# Category (level_1 > level_2) -> Kraljic classification
CATEGORY_KRALJIC_MAP: dict[tuple[str, str], str] = {
    ("Goods", "Fabrics"): "Strategic",
    ("Goods", "Yarns"): "Strategic",
    ("Goods", "Leathers"): "Strategic",
    ("Goods", "Chemical Products"): "Strategic",
    ("Manufacturing", "Outsourcing"): "Strategic",
    ("Manufacturing", "Outsourced Fabric and Yarn Processing"): "Strategic",
    ("Manufacturing", "Garment Manufacturing / Confection"): "Strategic",
    ("Services", "IT"): "Bottleneck",
    ("Services", "Plant and Machinery Maintenance"): "Bottleneck",
    ("Services", "Facilities Management"): "Leverage",
    ("Transportation", "Freight Transport / Logistics"): "Leverage",
    ("Fixed Assets", "Fixed Assets"): "Leverage",
    ("Services", "General Services"): "Non-Critical",
    ("Services", "General Administrative Services"): "Non-Critical",
    ("Transportation", "Passenger Transport"): "Non-Critical",
    ("Goods", "Packaging, Tubes and Pallets"): "Non-Critical",
}

KRALJIC_MONITORING: dict[str, str] = {
    "Strategic": "Quarterly or six-month review depending on category",
    "Bottleneck": "Six-month review",
    "Leverage": "Six-month or annual review",
    "Non-Critical": "Annual review",
}

COMMON_DOCUMENTS = [
    "Supplier Code",
    "Code of Ethics",
    "FORM1 general questionnaire",
    "Company registration information",
    "Bank and payment information",
]

STRATEGIC_EXTRA_DOCUMENTS = [
    "FORM2 category-specific questionnaire",
    "Terms and Conditions",
    "SA8000 questionnaire",
    "Quality certification",
    "ESG certificates",
    "Traceability documents",
    "Audit report if high risk",
]

YARN_FABRIC_EXTRA = [
    "Material traceability document",
    "Recycled or certified fiber certificate if applicable",
    "REACH compliance if relevant",
]

CHEMICAL_EXTRA = [
    "REACH compliance",
    "Safety Data Sheet",
    "Environmental compliance documents",
]

MANUFACTURING_EXTRA = [
    "Process capability information",
    "Quality control procedure",
    "Subcontracting transparency document",
    "Social responsibility documents",
]

RISK_CHECKS = [
    "Financial stability",
    "Geopolitical exposure",
    "Single sourcing dependency",
    "Raw material traceability",
    "Delivery reliability",
    "Quality history",
    "ESG compliance",
    "Certificate expiry risk",
]

ESG_CHECKS = [
    "ESG compliance",
    "SA8000 / social responsibility alignment",
    "Environmental certificates",
    "Traceability and recycled-content claims",
]

WORKFLOW_REMINDERS_BASE = [
    "Send FORM1",
    "Request missing documents",
    "Trigger certificate expiry reminder",
    "Trigger SAP code creation task reminder",
    "Ask buyer to confirm final qualification status",
]

QUALIFICATION_PATH_BASE = [
    "Pre-qualification",
    "FORM1 general questionnaire",
    "External risk assessment",
    "SAP code creation task reminder",
    "FORM2 category-specific qualification",
    "ESG assessment",
    "Buyer confirmation",
    "Possible audit if high risk",
]

ROUTER_KEYWORDS = [
    "new supplier",
    "supplier onboarding",
    "supplier qualification",
    "qualification process",
    "required documents",
    "documents are required",
    "documents are needed",
    "documents needed",
    "form1",
    "form2",
    "sap code",
    "esg documents",
    "supplier category",
    "kraljic",
    "yarn supplier",
    "fabric supplier",
    "chemical supplier",
    "chemical product",
    "logistics supplier",
    "outsourcing supplier",
    "outsourced manufacturing",
    "before creating an sap code",
    "general service supplier",
    "buyer check",
    "what should the buyer",
]

_CATEGORY_HINTS: list[tuple[list[str], str, str]] = [
    (["yarn", "yarns"], "Goods", "Yarns"),
    (["fabric", "fabrics"], "Goods", "Fabrics"),
    (["leather", "leathers"], "Goods", "Leathers"),
    (["chemical", "chemicals", "sds", "reach"], "Goods", "Chemical Products"),
    (["logistics", "freight", "transport", "shipping"], "Transportation", "Freight Transport / Logistics"),
    (["outsourc", "subcontract", "garment manufacturing", "confection"], "Manufacturing", "Outsourcing"),
    (["fabric and yarn processing", "yarn processing"], "Manufacturing", "Outsourced Fabric and Yarn Processing"),
    (["packaging", "pallet", "tube"], "Goods", "Packaging, Tubes and Pallets"),
    (["it service", "information technology"], "Services", "IT"),
    (["maintenance", "plant and machinery"], "Services", "Plant and Machinery Maintenance"),
    (["facilities management", "facility management"], "Services", "Facilities Management"),
    (["general administrative", "administrative service"], "Services", "General Administrative Services"),
    (["general service", "general services"], "Services", "General Services"),
    (["passenger transport"], "Transportation", "Passenger Transport"),
    (["fixed asset"], "Fixed Assets", "Fixed Assets"),
]


def detect_qualification_checklist_intent(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in ROUTER_KEYWORDS)


def apply_qualification_router_override(parsed: dict[str, Any], question: str) -> dict[str, Any]:
    """Boost qualification_checklist when onboarding keywords are present."""
    if not detect_qualification_checklist_intent(question):
        return parsed
    if parsed.get("intent") == "policy_qa" or float(parsed.get("confidence", 0)) < 0.85:
        parsed = dict(parsed)
        parsed["intent"] = "qualification_checklist"
        parsed["confidence"] = max(float(parsed.get("confidence", 0)), 0.9)
        parsed["reason"] = (parsed.get("reason") or "") + " (keyword match: supplier qualification checklist)"
    return parsed


def extract_qualification_input(question: str) -> dict[str, Any]:
    """Extract supplier qualification fields from natural language (rule-based, no fabrication)."""
    q = question.lower()
    data: dict[str, Any] = {
        "supplier_name": None,
        "country": None,
        "category_level_1": None,
        "category_level_2": None,
        "provided_product_or_service": None,
        "risk_level": None,
        "previous_relationship": None,
        "special_notes": None,
    }

    for pattern, country in [
        (r"\bchina\b", "China"),
        (r"\bitaly\b", "Italy"),
        (r"\bvietnam\b", "Vietnam"),
        (r"\bgermany\b", "Germany"),
        (r"\bindia\b", "India"),
        (r"\bturkey\b", "Turkey"),
        (r"\bportugal\b", "Portugal"),
    ]:
        if re.search(pattern, q):
            data["country"] = country
            break

    if "high risk" in q or "high-risk" in q:
        data["risk_level"] = "high"
    elif "low risk" in q:
        data["risk_level"] = "low"

    if any(t in q for t in ["existing supplier", "already work", "previous relationship", "renew"]):
        data["previous_relationship"] = "existing"

    for hints, level_1, level_2 in _CATEGORY_HINTS:
        if any(h in q for h in hints):
            data["category_level_1"] = level_1
            data["category_level_2"] = level_2
            data["provided_product_or_service"] = level_2
            break

    if "sap code" in q and not data["category_level_1"]:
        data["special_notes"] = (data.get("special_notes") or "") + " SAP code creation mentioned."

    return data


def needs_category_clarification(input_data: dict[str, Any]) -> bool:
    return not (input_data.get("category_level_1") and input_data.get("category_level_2"))


def build_clarification_question(input_data: dict[str, Any], lang: str = "en") -> str:
    if lang == "zh":
        return (
            "在进入供应商准入清单前，请先补充供应商类别，例如：纱线、面料、化工品、物流、"
            "外包制造或一般服务。如有国家/地区或风险等级也请一并说明。"
        )
    return (
        "Could you specify the supplier category, such as yarns, fabrics, chemical products, "
        "logistics, outsourced manufacturing, or general services? "
        "If known, please also share country/region and any risk context."
    )


def _category_key(level_1: str, level_2: str) -> tuple[str, str]:
    return (level_1.strip(), level_2.strip())


def _extra_documents(level_1: str, level_2: str) -> list[str]:
    extras: list[str] = []
    key = _category_key(level_1, level_2)
    kraljic = CATEGORY_KRALJIC_MAP.get(key, "Strategic")
    if kraljic == "Strategic":
        extras.extend(STRATEGIC_EXTRA_DOCUMENTS)
    if level_2 in {"Yarns", "Fabrics", "Leathers"}:
        extras.extend(YARN_FABRIC_EXTRA)
    if level_2 == "Chemical Products":
        extras.extend(CHEMICAL_EXTRA)
    if level_1 == "Manufacturing":
        extras.extend(MANUFACTURING_EXTRA)
    # de-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for doc in extras:
        if doc not in seen:
            seen.add(doc)
            out.append(doc)
    return out


def _workflow_reminders(level_1: str, level_2: str, risk_level: str | None) -> list[str]:
    reminders = list(WORKFLOW_REMINDERS_BASE)
    key = _category_key(level_1, level_2)
    kraljic = CATEGORY_KRALJIC_MAP.get(key, "Strategic")
    if kraljic in {"Strategic", "Bottleneck"}:
        reminders.insert(1, f"Send FORM2 for {level_2.lower()} category")
    if level_2 in {"Yarns", "Fabrics"}:
        reminders.append("Request ESG and traceability certificates")
    if level_2 == "Chemical Products":
        reminders.append("Request REACH, SDS, and environmental compliance documents")
    if level_1 == "Manufacturing":
        reminders.append("Request process capability and subcontracting transparency documents")
    if risk_level == "high":
        reminders.append("Schedule external audit if high risk")
    return reminders


def generate_qualification_checklist(input_data: dict[str, Any]) -> dict[str, Any]:
    level_1 = input_data.get("category_level_1") or ""
    level_2 = input_data.get("category_level_2") or ""
    key = _category_key(level_1, level_2)
    recommended_category = f"{level_1} > {level_2}"
    kraljic = CATEGORY_KRALJIC_MAP.get(key, "Strategic")
    monitoring = KRALJIC_MONITORING.get(kraljic, KRALJIC_MONITORING["Strategic"])

    required_documents = list(COMMON_DOCUMENTS)
    required_documents.extend(_extra_documents(level_1, level_2))
    seen: set[str] = set()
    required_documents = [d for d in required_documents if not (d in seen or seen.add(d))]

    risk_level = (input_data.get("risk_level") or "medium").lower()
    if risk_level == "high":
        suggested_status = "Qualified with Reserve — external risk check and possible audit required"
        next_action = (
            f"Send FORM1 and request {level_2.lower()}-specific documents; "
            "complete external risk assessment before category-based qualification."
        )
    elif kraljic == "Strategic":
        suggested_status = "Qualified with Reserve before external risk check"
        next_action = (
            f"Send FORM1 and request {level_2.lower()}-specific documents "
            "before moving to category-based qualification."
        )
    elif kraljic == "Non-Critical":
        suggested_status = "Provisional qualification — simplified path"
        next_action = "Send FORM1 and core compliance documents; annual review cadence applies."
    else:
        suggested_status = "Provisional qualification — standard review path"
        next_action = "Send FORM1 and category documents; confirm monitoring cadence with procurement."

    country = input_data.get("country")
    supplier = input_data.get("supplier_name")
    explanation_parts = [
        f"Checklist generated for Ratti supplier qualification ({recommended_category}).",
        f"Kraljic: {kraljic} item → {monitoring}.",
    ]
    if country:
        explanation_parts.append(f"Country context: {country}.")
    if supplier:
        explanation_parts.append(f"Supplier: {supplier}.")
    explanation_parts.append(
        "Workflow reminders below are simulated suggestions only — not integrated with SAP or email."
    )

    return {
        "recommended_category": recommended_category,
        "kraljic_classification": f"{kraljic} Item",
        "monitoring_frequency": monitoring,
        "qualification_path": list(QUALIFICATION_PATH_BASE),
        "required_documents": required_documents,
        "esg_checks": list(ESG_CHECKS),
        "risk_checks": list(RISK_CHECKS),
        "workflow_reminders": _workflow_reminders(level_1, level_2, input_data.get("risk_level")),
        "suggested_status": suggested_status,
        "next_action": next_action,
        "explanation": " ".join(explanation_parts),
    }


def format_checklist_markdown(result: dict[str, Any], lang: str = "en") -> str:
    docs = "\n".join(f"- [ ] {doc}" for doc in result.get("required_documents", []))
    path = "\n".join(f"{i}. {step}" for i, step in enumerate(result.get("qualification_path", []), start=1))
    esg_risk = "\n".join(f"- {item}" for item in result.get("risk_checks", []))
    reminders = "\n".join(f"- {item}" for item in result.get("workflow_reminders", []))

    if lang == "zh":
        title = "### 供应商准入清单"
        sim_note = "**模拟流程提醒（非 SAP/邮件集成）**"
    else:
        title = "### Supplier Qualification Checklist"
        sim_note = "**Simulated workflow reminders** _(not integrated with SAP or email)_"

    return f"""{title}

**Recommended category:** {result.get("recommended_category", "n/a")}  
**Kraljic classification:** {result.get("kraljic_classification", "n/a")}  
**Monitoring frequency:** {result.get("monitoring_frequency", "n/a")}  

**Qualification path**
{path}

**Required documents**
{docs}

**ESG / Risk checks**
{esg_risk}

{sim_note}
{reminders}

**Suggested status:** {result.get("suggested_status", "n/a")}  
**Next action:** {result.get("next_action", "n/a")}

_{result.get("explanation", "")}_
"""
