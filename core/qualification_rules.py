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
]

CONDITIONAL_DOCUMENTS_BASE = [
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

QUALIFICATION_PATH_BASE = [
    "Initial supplier contact",
    "FORM1 general questionnaire",
    "Basic document acceptance check",
    "External risk assessment",
    "SAP code creation task reminder",
    "FORM2 category-specific qualification",
    "ESG assessment",
    "Buyer confirmation",
    "Possible audit if high risk",
]

_CATEGORY_LEVEL1_ZH = {
    "Goods": "商品",
    "Manufacturing": "制造",
    "Services": "服务",
    "Transportation": "运输",
    "Fixed Assets": "固定资产",
}

_CATEGORY_LEVEL2_ZH = {
    "Yarns": "纱线",
    "Fabrics": "面料",
    "Leathers": "皮革",
    "Chemical Products": "化工品",
    "Outsourcing": "外包",
    "Outsourced Fabric and Yarn Processing": "面料与纱线外发加工",
    "Garment Manufacturing / Confection": "服装制造",
    "IT": "IT",
    "Plant and Machinery Maintenance": "设备与机械维护",
    "Facilities Management": "设施管理",
    "General Services": "一般服务",
    "General Administrative Services": "一般行政服务",
    "Freight Transport / Logistics": "货运与物流",
    "Passenger Transport": "客运",
    "Fixed Assets": "固定资产",
    "Packaging, Tubes and Pallets": "包装、纸管与托盘",
}

_COUNTRY_ZH = {
    "China": "中国",
    "Italy": "意大利",
    "Germany": "德国",
    "Turkey": "土耳其",
    "Vietnam": "越南",
    "India": "印度",
    "Portugal": "葡萄牙",
    "Not specified": "未指定",
}

_KRALJIC_ZH = {
    "Strategic": "战略类物料",
    "Bottleneck": "瓶颈类物料",
    "Leverage": "杠杆类物料",
    "Non-Critical": "非关键类物料",
}

_MONITORING_ZH = {
    "Quarterly review": "季度评审",
    "Six-month review": "半年度评审",
    "Six-month or annual review": "半年度或年度评审",
    "Annual review": "年度评审",
    "Quarterly or six-month review depending on category": "按品类季度或半年度评审",
}

_TEXT_ZH: dict[str, str] = {
    # Qualification path
    "Initial supplier contact": "初步供应商联系",
    "FORM1 general questionnaire": "FORM1 通用问卷",
    "Basic document acceptance check": "基础文件验收检查",
    "External risk assessment": "外部风险评估",
    "SAP code creation task reminder": "SAP 编码创建任务提醒（模拟）",
    "FORM2 category-specific qualification": "FORM2 品类专项准入",
    "ESG assessment": "ESG 评估",
    "Buyer confirmation": "采购员确认",
    "Possible audit if high risk": "高风险情况下可能审计",
    # Documents
    "Supplier Code": "供应商代码",
    "Code of Ethics": "道德准则",
    "Company registration information": "公司注册信息",
    "Bank and payment information": "银行与付款信息",
    "FORM2 category-specific questionnaire": "FORM2 品类专项问卷",
    "Terms and Conditions": "条款与条件",
    "SA8000 questionnaire": "SA8000 问卷",
    "Quality certification": "质量认证",
    "ESG certificates": "ESG 证书",
    "Traceability documents": "可追溯性文件",
    "Audit report if high risk": "高风险审计报告（如适用）",
    "Material traceability document": "材料可追溯性文件",
    "Recycled or certified fiber certificate if applicable": "再生或认证纤维证书（如适用）",
    "REACH compliance if relevant": "REACH 合规（如适用）",
    "REACH compliance": "REACH 合规",
    "Safety Data Sheet": "安全数据表（SDS）",
    "Environmental compliance documents": "环境合规文件",
    "Process capability information": "工艺能力信息",
    "Quality control procedure": "质量控制程序",
    "Subcontracting transparency document": "分包透明度文件",
    "Social responsibility documents": "社会责任文件",
    "Additional traceability evidence if subcontracting is involved": "如涉及分包，需补充可追溯性证据",
    # Risk checks
    "Financial stability": "财务稳定性",
    "Geopolitical exposure": "地缘政治暴露",
    "Single sourcing dependency": "单一来源依赖",
    "Raw material traceability": "原材料可追溯性",
    "Delivery reliability": "交付可靠性",
    "Quality history": "质量历史",
    "ESG compliance": "ESG 合规",
    "Certificate expiry risk": "证书到期风险",
  # ESG checks (subset overlaps with risk checks)
    "SA8000 / social responsibility alignment": "SA8000 / 社会责任对齐",
    "Environmental certificates": "环境类证书",
    "Traceability and recycled-content claims": "可追溯性与再生含量声明",
}


def _lang_code(lang: str | None) -> str:
    return "zh" if (lang or "en").lower().startswith("zh") else "en"


def resolve_response_language(explicit_lang: str | None, question: str) -> str:
    """Prefer explicit UI language; infer Chinese from question text when needed."""
    if re.search(r"[\u4e00-\u9fff]", question or ""):
        return "zh"
    return _lang_code(explicit_lang)


def _t(text: str, lang: str) -> str:
    if _lang_code(lang) != "zh":
        return text
    return _TEXT_ZH.get(text, text)


def _t_list(items: list[str], lang: str) -> list[str]:
    return [_t(item, lang) for item in items]


def _recommended_category(level_1: str, level_2: str, lang: str) -> str:
    if _lang_code(lang) != "zh":
        return f"{level_1} > {level_2}"
    l1 = _CATEGORY_LEVEL1_ZH.get(level_1, level_1)
    l2 = _CATEGORY_LEVEL2_ZH.get(level_2, level_2)
    return f"{l1} > {l2}"


def _country_display(country: str, lang: str) -> str:
    if _lang_code(lang) != "zh":
        return country
    return _COUNTRY_ZH.get(country, country)


def _kraljic_display(kraljic: str, lang: str) -> str:
    if _lang_code(lang) != "zh":
        return f"{kraljic} Item"
    return _KRALJIC_ZH.get(kraljic, kraljic)


def _monitoring_display(monitoring: str, lang: str) -> str:
    if _lang_code(lang) != "zh":
        return monitoring
    return _MONITORING_ZH.get(monitoring, monitoring)


def _category_label_zh(level_2: str) -> str:
    return _CATEGORY_LEVEL2_ZH.get(level_2, level_2)

# Strategic goods categories reviewed quarterly (Ratti cadence).
STRATEGIC_QUARTERLY_CATEGORIES: set[tuple[str, str]] = {
    ("Goods", "Yarns"),
    ("Goods", "Fabrics"),
    ("Goods", "Leathers"),
    ("Goods", "Chemical Products"),
    ("Manufacturing", "Outsourcing"),
    ("Manufacturing", "Outsourced Fabric and Yarn Processing"),
    ("Manufacturing", "Garment Manufacturing / Confection"),
}

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
    "纱线",
    "纱线供应商",
    "准入流程",
    "供应商准入",
    "新供应商",
]

# Longer phrases first to avoid partial matches (e.g. yarn processing before yarn).
CATEGORY_SYNONYMS: list[tuple[list[str], str, str]] = [
    (["纱线供应商", "yarn supplier", "纱线", "yarns", "yarn"], "Goods", "Yarns"),
    (["fabric and yarn processing", "纱线加工", "yarn processing"], "Manufacturing", "Outsourced Fabric and Yarn Processing"),
    (["面料", "布料", "fabric supplier", "fabrics", "fabric"], "Goods", "Fabrics"),
    (["皮革", "leathers", "leather"], "Goods", "Leathers"),
    (["化工品", "化学品", "chemical products", "chemical product", "chemicals", "chemical"], "Goods", "Chemical Products"),
    (["物流", "运输", "货运", "logistics supplier", "freight transport", "freight", "logistics", "transportation"], "Transportation", "Freight Transport / Logistics"),
    (["服装制造", "成衣制造", "garment manufacturing", "confection"], "Manufacturing", "Garment Manufacturing / Confection"),
    (["外包制造", "外发加工", "outsourced manufacturing", "outsourcing", "outsourc", "subcontract"], "Manufacturing", "Outsourcing"),
    (["设备维护", "机械维护", "plant and machinery maintenance", "plant maintenance", "machinery maintenance", "plant and machinery"], "Services", "Plant and Machinery Maintenance"),
    (["设施管理", "facilities management", "facility management"], "Services", "Facilities Management"),
    (["一般行政", "general administrative", "administrative service"], "Services", "General Administrative Services"),
    (["一般服务", "general services", "general service"], "Services", "General Services"),
    (["it service", "information technology", "software", "hardware", "软件", "硬件"], "Services", "IT"),
    (["packaging", "pallet", "tube", "包装"], "Goods", "Packaging, Tubes and Pallets"),
    (["passenger transport", "客运"], "Transportation", "Passenger Transport"),
    (["fixed asset", "固定资产"], "Fixed Assets", "Fixed Assets"),
]

COUNTRY_SYNONYMS: list[tuple[list[str], str]] = [
    (["来自中国", "中国", "china", "chinese"], "China"),
    (["来自意大利", "意大利", "italy", "italian"], "Italy"),
    (["来自德国", "德国", "germany", "german"], "Germany"),
    (["来自土耳其", "土耳其", "turkey", "turkish"], "Turkey"),
    (["来自越南", "越南", "vietnam", "vietnamese"], "Vietnam"),
    (["来自印度", "印度", "india", "indian"], "India"),
    (["来自葡萄牙", "葡萄牙", "portugal", "portuguese"], "Portugal"),
]


POLICY_EXPLANATION_HINTS = [
    "why do ",
    "why are ",
    "why does ",
    "what is the difference",
    "how is ",
    "how often",
    "which categories",
    "explain the ",
    "explain how",
]


def is_policy_explanation_question(question: str) -> bool:
    q = (question or "").lower()
    return any(h in q for h in POLICY_EXPLANATION_HINTS)


def detect_qualification_checklist_intent(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in ROUTER_KEYWORDS)


def apply_qualification_router_override(parsed: dict[str, Any], question: str) -> dict[str, Any]:
    """Boost qualification_checklist when onboarding keywords are present."""
    if is_policy_explanation_question(question):
        return parsed
    if not detect_qualification_checklist_intent(question):
        return parsed
    if parsed.get("intent") == "qualification_checklist":
        return parsed
    if float(parsed.get("confidence", 0)) >= 0.85:
        return parsed
    parsed = dict(parsed)
    parsed["intent"] = "qualification_checklist"
    parsed["confidence"] = max(float(parsed.get("confidence", 0)), 0.9)
    parsed["reason"] = (parsed.get("reason") or "") + " (keyword match: supplier qualification checklist)"
    return parsed


def _text_contains(text: str, text_lower: str, phrase: str) -> bool:
    """Match English case-insensitively; match CJK phrases on original text."""
    if any("\u4e00" <= c <= "\u9fff" for c in phrase):
        return phrase in text
    return phrase.lower() in text_lower


def _extract_country(text: str, text_lower: str) -> str | None:
    for hints, country in COUNTRY_SYNONYMS:
        if any(_text_contains(text, text_lower, h) for h in hints):
            return country
    return None


def _extract_category(text: str, text_lower: str) -> tuple[str | None, str | None]:
    for hints, level_1, level_2 in CATEGORY_SYNONYMS:
        if any(_text_contains(text, text_lower, h) for h in hints):
            return level_1, level_2
    return None, None


def extract_qualification_input(question: str) -> dict[str, Any]:
    """Extract supplier qualification fields from natural language (rule-based, no fabrication)."""
    text = question.strip()
    text_lower = text.lower()
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

    data["country"] = _extract_country(text, text_lower)

    if any(
        _text_contains(text, text_lower, t)
        for t in ["high risk", "high-risk", "高风险", "高风险供应商"]
    ):
        data["risk_level"] = "high"
    elif any(_text_contains(text, text_lower, t) for t in ["low risk", "低风险"]):
        data["risk_level"] = "low"

    if any(
        _text_contains(text, text_lower, t)
        for t in [
            "existing supplier",
            "already work",
            "previous relationship",
            "renew",
            "已有供应商",
            "现有供应商",
        ]
    ):
        data["previous_relationship"] = "existing"
    elif _text_contains(text, text_lower, "new supplier") or re.search(
        r"新\S{0,6}供应商", text
    ):
        data["previous_relationship"] = "New"

    level_1, level_2 = _extract_category(text, text_lower)
    if level_1 and level_2:
        data["category_level_1"] = level_1
        data["category_level_2"] = level_2
        data["provided_product_or_service"] = level_2

    if _text_contains(text, text_lower, "sap code") and not data["category_level_1"]:
        data["special_notes"] = (data.get("special_notes") or "") + " SAP code creation mentioned."

    return data


def normalize_qualification_input(input_data: dict[str, Any]) -> dict[str, Any]:
    """Apply safe defaults for optional fields; never invent category."""
    data = dict(input_data)
    if not data.get("risk_level"):
        data["risk_level"] = "Unknown"
    if not data.get("previous_relationship"):
        data["previous_relationship"] = "New"
    if not data.get("country"):
        data["country"] = "Not specified"
    if data.get("category_level_2") and not data.get("provided_product_or_service"):
        data["provided_product_or_service"] = data["category_level_2"]
    return data


def needs_category_clarification(input_data: dict[str, Any]) -> bool:
    level_2 = input_data.get("category_level_2") or input_data.get("provided_product_or_service")
    return not level_2


def build_clarification_question(input_data: dict[str, Any], lang: str = "en") -> str:
    if lang == "zh":
        return (
            "请补充供应商类别，例如：纱线、面料、化工品、物流、外包制造或一般服务。"
        )
    return (
        "Could you specify the supplier category, such as yarns, fabrics, chemical products, "
        "logistics, outsourced manufacturing, or general services?"
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


def _monitoring_frequency(level_1: str, level_2: str, kraljic: str) -> str:
    key = _category_key(level_1, level_2)
    if key in STRATEGIC_QUARTERLY_CATEGORIES:
        return "Quarterly review"
    return KRALJIC_MONITORING.get(kraljic, KRALJIC_MONITORING["Strategic"])


def _conditional_documents(level_1: str, level_2: str) -> list[str]:
    docs = list(CONDITIONAL_DOCUMENTS_BASE)
    if level_1 == "Manufacturing" or level_2 in {
        "Outsourcing",
        "Outsourced Fabric and Yarn Processing",
        "Garment Manufacturing / Confection",
    }:
        docs.append("Additional traceability evidence if subcontracting is involved")
    return docs


def _workflow_reminders(level_1: str, level_2: str, risk_level: str | None, lang: str = "en") -> list[str]:
    category_en = level_2.lower() if level_2 else "supplier"
    category_zh = _category_label_zh(level_2) if level_2 else "供应商"
    if _lang_code(lang) == "zh":
        reminders = [
            "发送 FORM1",
            f"发送 FORM2（{category_zh}品类）",
            "催交缺失的 ESG、可追溯性及品类专项文件",
            "触发证书到期提醒（模拟）",
            "触发 SAP 编码创建任务提醒（模拟）",
            "请采购员确认最终准入状态",
        ]
        if level_2 == "Chemical Products":
            reminders[2] = "催交缺失的 REACH、SDS、环境合规及品类专项文件"
        if risk_level == "high":
            reminders.append("如为高风险，安排外部审计")
        return reminders

    reminders = [
        "Send FORM1",
        f"Send FORM2 for {category_en} category",
        "Request missing ESG, traceability and category-specific documents",
        "Trigger certificate expiry reminder",
        "Trigger SAP code creation task reminder",
        "Ask buyer to confirm final qualification status",
    ]
    if level_2 == "Chemical Products":
        reminders[2] = "Request missing REACH, SDS, environmental and category-specific documents"
    if risk_level == "high":
        reminders.append("Schedule external audit if high risk")
    return reminders


def _suggested_status_and_action(
    level_2: str, kraljic: str, risk_level: str, lang: str = "en"
) -> tuple[str, str]:
    category_en = level_2.lower() if level_2 else "supplier"
    category_zh = _category_label_zh(level_2) if level_2 else "供应商"

    if _lang_code(lang) == "zh":
        if risk_level == "high":
            return (
                "附条件合格——需完成外部风险核查，必要时安排审计",
                (
                    f"发送 FORM1，并索取{category_zh}品类专项文件；"
                    "在进入品类专项准入前完成外部风险评估。"
                ),
            )
        if kraljic == "Strategic":
            return (
                "初步附条件合格（FORM1 完成且基础文件验收后）；"
                "最终状态待外部风险评估及采购员确认。",
                f"发送 FORM1，并索取{category_zh}品类专项准入文件，再进入品类专项准入阶段。",
            )
        if kraljic == "Non-Critical":
            return (
                "临时准入——简化流程",
                "发送 FORM1 及核心合规文件；按年度评审周期管理。",
            )
        return (
            "临时准入——标准流程",
            "发送 FORM1 及品类文件；与采购确认监控频率。",
        )

    if risk_level == "high":
        return (
            "Qualified with Reserve — external risk check and possible audit required",
            (
                f"Send FORM1 and request {category_en}-specific documents; "
                "complete external risk assessment before category-based qualification."
            ),
        )
    if kraljic == "Strategic":
        return (
            "Preliminary Qualified with Reserve after FORM1 completion and basic document acceptance; "
            "final status pending external risk assessment and buyer confirmation.",
            (
                f"Send FORM1 and request {category_en}-specific qualification documents "
                "before moving to category-based qualification."
            ),
        )
    if kraljic == "Non-Critical":
        return (
            "Provisional qualification — simplified path",
            "Send FORM1 and core compliance documents; annual review cadence applies.",
        )
    return (
        "Provisional qualification — standard review path",
        "Send FORM1 and category documents; confirm monitoring cadence with procurement.",
    )


def generate_qualification_checklist(input_data: dict[str, Any], lang: str = "en") -> dict[str, Any]:
    level_1 = input_data.get("category_level_1") or ""
    level_2 = input_data.get("category_level_2") or ""
    key = _category_key(level_1, level_2)
    recommended_category = _recommended_category(level_1, level_2, lang)
    kraljic = CATEGORY_KRALJIC_MAP.get(key, "Strategic")
    monitoring_en = _monitoring_frequency(level_1, level_2, kraljic)
    monitoring = _monitoring_display(monitoring_en, lang)

    required_documents = list(COMMON_DOCUMENTS)
    required_documents.extend(_extra_documents(level_1, level_2))
    seen: set[str] = set()
    required_documents = [d for d in required_documents if not (d in seen or seen.add(d))]

    risk_level = (input_data.get("risk_level") or "unknown").lower()
    country = _country_display(input_data.get("country") or "Not specified", lang)
    supplier = input_data.get("supplier_name")
    suggested_status, next_action = _suggested_status_and_action(level_2, kraljic, risk_level, lang)
    conditional_documents = _t_list(_conditional_documents(level_1, level_2), lang)

    return {
        "recommended_category": recommended_category,
        "supplier_country": country,
        "kraljic_classification": _kraljic_display(kraljic, lang),
        "monitoring_frequency": monitoring,
        "qualification_path": _t_list(list(QUALIFICATION_PATH_BASE), lang),
        "required_documents": _t_list(required_documents, lang),
        "conditional_documents": conditional_documents,
        "esg_checks": _t_list(list(ESG_CHECKS), lang),
        "risk_checks": _t_list(list(RISK_CHECKS), lang),
        "workflow_reminders": _workflow_reminders(level_1, level_2, input_data.get("risk_level"), lang),
        "suggested_status": suggested_status,
        "next_action": next_action,
    }


def format_checklist_markdown(result: dict[str, Any], lang: str = "en") -> str:
    docs = "\n".join(f"- {doc}" for doc in result.get("required_documents", []))
    conditional = "\n".join(f"- {doc}" for doc in result.get("conditional_documents", []))
    path = "\n".join(f"{i}. {step}" for i, step in enumerate(result.get("qualification_path", []), start=1))
    esg_risk = "\n".join(f"- {item}" for item in result.get("risk_checks", []))
    reminders = "\n".join(f"- {item}" for item in result.get("workflow_reminders", []))

    country = result.get("supplier_country") or ("未指定" if _lang_code(lang) == "zh" else "Not specified")
    if _lang_code(lang) == "zh":
        title = "### 供应商准入清单"
        cat_label = "**推荐类别：**"
        country_label = "**供应商国家/地区：**"
        kraljic_label = "**Kraljic 分类：**"
        monitoring_label = "**监控频率：**"
        status_label = "**建议状态：**"
        next_label = "**下一步行动：**"
        path_h = "### 准入路径"
        docs_h = "### 必备文件"
        cond_h = "### 条件性文件 / 动作"
        risk_h = "### ESG / 风险检查"
        sim_h = "### 模拟流程提醒"
        sim_note = "_（非 SAP/邮件集成，仅为流程建议）_"
    else:
        title = "### Supplier Qualification Checklist"
        cat_label = "**Recommended category:**"
        country_label = "**Supplier country / region:**"
        kraljic_label = "**Kraljic classification:**"
        monitoring_label = "**Monitoring frequency:**"
        status_label = "**Suggested status:**"
        next_label = "**Next action:**"
        path_h = "### Qualification path"
        docs_h = "### Required documents"
        cond_h = "### Conditional documents / actions"
        risk_h = "### ESG / Risk checks"
        sim_h = "### Simulated workflow reminders"
        sim_note = "_(not integrated with SAP or email)_"

    conditional_block = f"\n{cond_h}\n{conditional}\n" if conditional else ""

    return f"""{title}

{cat_label} {result.get("recommended_category", "n/a")}  
{country_label} {country}  
{kraljic_label} {result.get("kraljic_classification", "n/a")}  
{monitoring_label} {result.get("monitoring_frequency", "n/a")}  

{path_h}
{path}

{docs_h}
{docs}
{conditional_block}
{risk_h}
{esg_risk}

{sim_h}
{reminders}

{sim_note}

{status_label} {result.get("suggested_status", "n/a")}  

{next_label} {result.get("next_action", "n/a")}
"""
