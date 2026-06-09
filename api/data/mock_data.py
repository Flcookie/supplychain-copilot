"""Demo workbench data — synthetic, no confidential supplier records."""

from __future__ import annotations

from typing import Any

SUPPLIERS: list[dict[str, Any]] = [
    {
        "id": "SUP021",
        "name": "TechFab Italia",
        "category": "Yarn",
        "country": "Italy",
        "rating": "C",
        "otd_rate": 0.631,
        "defect_rate": 0.034,
        "risk_level": "high",
        "status": "active",
        "contract_expiry": "2026-03-31",
        "last_review": "2025-09-15",
    },
    {
        "id": "SUP012",
        "name": "Nordic Yarn Co",
        "category": "Yarn",
        "country": "Norway",
        "rating": "C",
        "otd_rate": 0.912,
        "defect_rate": 0.018,
        "risk_level": "medium",
        "status": "active",
        "contract_expiry": "2026-06-30",
        "last_review": "2025-10-01",
    },
    {
        "id": "SUP003",
        "name": "SinoFabrics Ltd",
        "category": "Fabric",
        "country": "China",
        "rating": "A",
        "otd_rate": 0.953,
        "defect_rate": 0.012,
        "risk_level": "low",
        "status": "active",
        "contract_expiry": "2027-01-15",
        "last_review": "2025-08-20",
    },
    {
        "id": "SUP034",
        "name": "Guangzhou Textiles",
        "category": "Yarn",
        "country": "China",
        "rating": "B",
        "otd_rate": 0.82,
        "defect_rate": 0.022,
        "risk_level": "medium",
        "status": "active",
        "contract_expiry": "2026-02-28",
        "last_review": "2025-07-10",
    },
    {
        "id": "SUP019",
        "name": "Alpine Buttons SpA",
        "category": "Accessories",
        "country": "Italy",
        "rating": "B+",
        "otd_rate": 0.885,
        "defect_rate": 0.015,
        "risk_level": "low",
        "status": "active",
        "contract_expiry": "2026-11-30",
        "last_review": "2025-06-05",
    },
    {
        "id": "SUP055",
        "name": "Alpine Buttons SpA",
        "category": "Accessories",
        "country": "Italy",
        "rating": "B",
        "otd_rate": 0.871,
        "defect_rate": 0.019,
        "risk_level": "low",
        "status": "active",
        "contract_expiry": "2026-01-10",
        "last_review": "2025-05-12",
    },
    {
        "id": "SUP007",
        "name": "Mumbai Spinners",
        "category": "Yarn",
        "country": "India",
        "rating": "B+",
        "otd_rate": 0.898,
        "defect_rate": 0.016,
        "risk_level": "low",
        "status": "active",
        "contract_expiry": "2026-08-15",
        "last_review": "2025-09-01",
    },
    {
        "id": "SUP015",
        "name": "LeatherCraft Turkey",
        "category": "Leather",
        "country": "Turkey",
        "rating": "A-",
        "otd_rate": 0.921,
        "defect_rate": 0.014,
        "risk_level": "low",
        "status": "active",
        "contract_expiry": "2026-04-20",
        "last_review": "2025-08-15",
    },
    {
        "id": "SUP028",
        "name": "Porto Garment Works",
        "category": "Manufacturing",
        "country": "Portugal",
        "rating": "B",
        "otd_rate": 0.856,
        "defect_rate": 0.021,
        "risk_level": "medium",
        "status": "active",
        "contract_expiry": "2026-07-01",
        "last_review": "2025-10-20",
    },
    {
        "id": "SUP041",
        "name": "Shanghai Dye House",
        "category": "Fabric",
        "country": "China",
        "rating": "B+",
        "otd_rate": 0.889,
        "defect_rate": 0.017,
        "risk_level": "medium",
        "status": "active",
        "contract_expiry": "2026-05-30",
        "last_review": "2025-07-22",
    },
    {
        "id": "SUP048",
        "name": "EcoThread Vietnam",
        "category": "Yarn",
        "country": "Vietnam",
        "rating": "A",
        "otd_rate": 0.941,
        "defect_rate": 0.011,
        "risk_level": "low",
        "status": "active",
        "contract_expiry": "2027-03-15",
        "last_review": "2025-11-01",
    },
    {
        "id": "SUP052",
        "name": "Baltic Logistics",
        "category": "Services",
        "country": "Estonia",
        "rating": "B",
        "otd_rate": 0.862,
        "defect_rate": 0.0,
        "risk_level": "low",
        "status": "active",
        "contract_expiry": "2026-09-30",
        "last_review": "2025-04-18",
    },
    {
        "id": "SUP060",
        "name": "Precision MRO GmbH",
        "category": "Services",
        "country": "Germany",
        "rating": "A-",
        "otd_rate": 0.935,
        "defect_rate": 0.0,
        "risk_level": "low",
        "status": "active",
        "contract_expiry": "2026-12-31",
        "last_review": "2025-09-28",
    },
    {
        "id": "SUP009",
        "name": "Cotton Valley Egypt",
        "category": "Yarn",
        "country": "Egypt",
        "rating": "B-",
        "otd_rate": 0.798,
        "defect_rate": 0.026,
        "risk_level": "medium",
        "status": "active",
        "contract_expiry": "2026-03-01",
        "last_review": "2025-06-30",
    },
    {
        "id": "SUP036",
        "name": "Ratti Preferred Partner",
        "category": "Yarn",
        "country": "Italy",
        "rating": "A",
        "otd_rate": 0.967,
        "defect_rate": 0.009,
        "risk_level": "low",
        "status": "active",
        "contract_expiry": "2027-06-01",
        "last_review": "2025-11-15",
    },
]

REVIEW_QUEUE: list[dict[str, Any]] = [
    {
        "supplier_id": "SUP021",
        "priority": "P1",
        "reason": "OTD < 70% for 3 consecutive months",
        "due_date": "2025-12-15",
        "status": "pending",
    },
    {
        "supplier_id": "SUP012",
        "priority": "P2",
        "reason": "Vendor Rating dropped to C",
        "due_date": "2025-12-20",
        "status": "in_progress",
    },
    {
        "supplier_id": "SUP034",
        "priority": "P2",
        "reason": "ESG certificate expiring within 30 days",
        "due_date": "2025-12-30",
        "status": "pending",
    },
    {
        "supplier_id": "SUP055",
        "priority": "P3",
        "reason": "Routine pre-renewal review",
        "due_date": "2026-01-10",
        "status": "scheduled",
    },
]

POLICY_DOCS: list[dict[str, Any]] = [
    {
        "id": "POL-001",
        "title": "Supplier Code of Conduct v2.3",
        "category": "ESG",
        "last_updated": "2024-01",
        "scope": "All suppliers",
        "quick_question": "What are the key requirements for suppliers?",
    },
    {
        "id": "POL-002",
        "title": "Yarn Supplier ESG Qualification Requirements",
        "category": "ESG",
        "last_updated": "2024-06",
        "scope": "Yarn · China, India · High-risk regions",
        "quick_question": "What ESG documents are required for yarn suppliers from China?",
    },
    {
        "id": "POL-003",
        "title": "Vendor Rating Methodology",
        "category": "Quality",
        "last_updated": "2025-01",
        "scope": "All Active suppliers · Quarterly scoring",
        "quick_question": "What is the process for C-rated suppliers?",
    },
    {
        "id": "POL-004",
        "title": "Strategic Supplier Monitoring Policy",
        "category": "Procurement",
        "last_updated": "2024-09",
        "scope": "Strategic / Kraljic segment",
        "quick_question": "What monitoring applies to strategic yarn suppliers?",
    },
    {
        "id": "POL-005",
        "title": "Supplier Qualification & Onboarding SOP",
        "category": "Procurement",
        "last_updated": "2024-03",
        "scope": "New supplier onboarding",
        "quick_question": "What qualification process should we follow for a new yarn supplier?",
    },
    {
        "id": "POL-006",
        "title": "REACH & Chemical Compliance Guide",
        "category": "Compliance",
        "last_updated": "2024-11",
        "scope": "EU market suppliers",
        "quick_question": "What REACH compliance documents are required?",
    },
    {
        "id": "POL-007",
        "title": "Kraljic Category Segmentation Framework",
        "category": "Procurement",
        "last_updated": "2023-12",
        "scope": "Category management",
        "quick_question": "How are yarn suppliers classified in Kraljic matrix?",
    },
    {
        "id": "POL-008",
        "title": "Human Rights & SA8000 Alignment",
        "category": "ESG",
        "last_updated": "2024-05",
        "scope": "Manufacturing & high-risk countries",
        "quick_question": "What SA8000 requirements apply to manufacturing suppliers?",
    },
]

KPI_TREND: dict[str, dict[str, Any]] = {
    "SUP021": {
        "otd": [0.70, 0.63, 0.58, 0.65, 0.61, 0.63],
        "defect": [0.025, 0.028, 0.031, 0.034, 0.033, 0.034],
        "months": ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
    "SUP012": {
        "otd": [0.95, 0.93, 0.91, 0.90, 0.91, 0.912],
        "defect": [0.012, 0.014, 0.016, 0.017, 0.018, 0.018],
        "months": ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
    "SUP034": {
        "otd": [0.85, 0.84, 0.83, 0.82, 0.81, 0.82],
        "defect": [0.018, 0.019, 0.020, 0.021, 0.022, 0.022],
        "months": ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
    "SUP003": {
        "otd": [0.94, 0.945, 0.95, 0.951, 0.952, 0.953],
        "defect": [0.013, 0.012, 0.012, 0.011, 0.012, 0.012],
        "months": ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
}

RISK_ALERTS: list[dict[str, Any]] = [
    {
        "supplier_id": "SUP021",
        "severity": "high",
        "message": "TechFab Italia · OTD below 70% for 3 consecutive months",
        "ask_ai_question": "Why is TechFab Italia (SUP021) at high risk and what actions should we take?",
    },
    {
        "supplier_id": "SUP034",
        "severity": "medium",
        "message": "Guangzhou Textiles · ESG certificate expiring within 30 days",
        "ask_ai_question": "What ESG documents does Guangzhou Textiles (SUP034) need to renew?",
    },
    {
        "supplier_id": "SUP012",
        "severity": "medium",
        "message": "Nordic Yarn Co · C rating — review explanation pending",
        "ask_ai_question": "Why did supplier SUP012 receive a C rating?",
    },
]

DASHBOARD_SUMMARY = {
    "active_suppliers": 87,
    "at_risk_suppliers": 6,
    "reviews_due_this_month": 4,
    "open_qualifications": 3,
    "greeting": "Good morning, Sarah.",
    "period_label": "Week 23 — Q2 2025",
    "yarn_kpi_snapshot": {
        "otd_rate": 0.873,
        "otd_target": 0.92,
        "defect_rate": 0.021,
        "defect_target": 0.015,
        "lead_time_days": 14.2,
        "lead_time_target": 12.0,
    },
}


def get_supplier(supplier_id: str) -> dict[str, Any] | None:
    for s in SUPPLIERS:
        if s["id"] == supplier_id:
            return s
    return None


def filter_suppliers(
    *,
    category: str | None = None,
    risk_level: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    rows = list(SUPPLIERS)
    if category:
        rows = [r for r in rows if r["category"].lower() == category.lower()]
    if risk_level:
        rows = [r for r in rows if r["risk_level"].lower() == risk_level.lower()]
    if status:
        rows = [r for r in rows if r["status"].lower() == status.lower()]
    if search:
        q = search.lower()
        rows = [
            r
            for r in rows
            if q in r["name"].lower() or q in r["id"].lower() or q in r["country"].lower()
        ]
    return rows
