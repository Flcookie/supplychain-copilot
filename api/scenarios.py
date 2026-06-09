"""Shared demo scenario templates for Streamlit and FastAPI."""

DEMO_SCENARIOS = {
    "en": [
        ("— Select a scenario template —", ""),
        (
            "Supplier qualification checklist",
            "We have a new yarn supplier from China. What qualification process should we follow?",
        ),
        (
            "Yarn supplier KPIs (2025)",
            "Show the on-time delivery rate and defect rate of yarn suppliers in 2025.",
        ),
        (
            "High-risk supplier review",
            "Which suppliers should be reviewed this month due to high risk?",
        ),
        ("Vendor rating explanation", "Why did supplier SUP012 receive a C rating?"),
        (
            "Policy & ESG Q&A",
            "What ESG documents are required for yarn suppliers under Ratti qualification policy?",
        ),
        (
            "Complex question (policy + KPI)",
            "For strategic yarn suppliers, what monitoring policy applies and what was their average on-time delivery in 2025?",
        ),
    ],
    "zh": [
        ("— 选择场景模板 —", ""),
        ("供应商准入清单", "我们有一家来自中国的新纱线供应商，准入流程应该怎么走？"),
        (
            "纱线供应商 KPI（2025）",
            "Show the on-time delivery rate and defect rate of yarn suppliers in 2025.",
        ),
        (
            "高风险供应商复审",
            "Which suppliers should be reviewed this month due to high risk?",
        ),
        ("Vendor Rating 解释", "Why did supplier SUP012 receive a C rating?"),
        ("政策与 ESG 问答", "纱线供应商准入需要哪些 ESG 文件？"),
        (
            "复合问题（政策 + KPI）",
            "战略纱线供应商需要哪些监控政策？他们在 2025 年的平均准时交付率是多少？",
        ),
    ],
}
