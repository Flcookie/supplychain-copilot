"""Deterministic SQL templates for Ratti supplier lifecycle KPIs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


_SUPPLIER_ID_PATTERN = re.compile(r"\b(SUP\d{3})\b", re.IGNORECASE)
_YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")


@dataclass
class TemplatedSQL:
    template_id: str
    sql: str
    params: tuple
    description: str


def _detect_supplier_ids(text: str) -> list[str]:
    return list(dict.fromkeys(m.upper() for m in _SUPPLIER_ID_PATTERN.findall(text or "")))


def _detect_year(text: str) -> Optional[str]:
    match = _YEAR_PATTERN.search(text or "")
    return match.group(1) if match else None


def _detect_category(text: str) -> Optional[str]:
    lowered = (text or "").lower()
    if "yarn" in lowered or "纱线" in text:
        return "Yarns"
    if "chemical" in lowered or "化工" in text or "化学品" in text:
        return "Chemical Products"
    if ("fabric" in lowered or "面料" in text or "布料" in text) and (
        "process" in lowered or "加工" in text
    ):
        return "Outsourced Fabric and Yarn Processing"
    if "fabric" in lowered or "面料" in text:
        return "Fabrics"
    return None


def _infer_metric_from_question(question: str) -> Optional[str]:
    text = (question or "").lower()
    q = question or ""
    if any(token in text for token in ["on-time", "on time", "ontime", "otd", "delivery rate"]) or any(
        t in q for t in ["准时交付", "交付率", "准时率"]
    ):
        return "on_time_rate"
    if any(token in text for token in ["defect rate", "defect_rate", "quality defect"]) or "缺陷率" in q:
        return "defect_rate"
    if any(token in text for token in ["vendor rating", "rating score", "rating class"]):
        return "vendor_rating"
    if any(token in text for token in ["spend", "annual spend"]):
        return "spend"
    if any(token in text for token in ["esg score", "esg"]):
        return "esg_score"
    if any(token in text for token in ["delay days", "average delay", "avg delay", "delivery delay"]):
        return "avg_delay_days"
    if any(token in text for token in ["expire", "expiry", "certificate"]):
        return "cert_expiry"
    if any(token in text for token in ["next step", "status"]):
        return "supplier_status"
    return None


def build_kpi_sql(question: str, kpi_parse: dict) -> Optional[TemplatedSQL]:
    """Return parameterized SQL when a deterministic Ratti template applies."""
    text = (question or "").lower()
    metric = (kpi_parse or {}).get("metric") or "other"
    if metric in {"other", "comparison", "trend"}:
        inferred = _infer_metric_from_question(question)
        if inferred:
            metric = inferred

    supplier_ids = _detect_supplier_ids(f"{question} {kpi_parse.get('supplier_hint', '') or ''}")
    category = _detect_category(question)
    year = _detect_year(question)

    # EVAL010 / Chinese yarn OTD + defect
    has_otd = any(
        t in text or t in (question or "")
        for t in ["on-time", "otd", "delivery rate", "准时交付", "交付率", "准时率"]
    )
    has_defect = "defect" in text or "缺陷率" in (question or "")
    if category == "Yarns" and has_defect and has_otd:
        period = year or "2025"
        return _yarn_otd_and_defect(period)

    if category == "Yarns" and has_otd and year:
        return _yarn_otd_and_defect(year)

    if metric == "avg_delay_days" and ("above 5" in text or "> 5" in text or "greater than 5" in text):
        return _avg_delay_above_threshold(5.0)

    if "kraljic" in text and "spend" in text:
        return _spend_by_kraljic()

    if metric == "cert_expiry" or ("expire" in text and "certificate" in text):
        return _certificates_expiring_soon(60)

    if "strategic" in text and ("vendor rating" in text or "rating score" in text or "rank" in text):
        return _strategic_vendor_rating_rank()

    if metric == "esg_score" and ("below 60" in text or "< 60" in text):
        return _esg_below_threshold_missing_docs(60)

    if len(supplier_ids) == 1 and ("next step" in text or "status" in text):
        return _supplier_status_snapshot(supplier_ids[0])

    if metric == "on_time_rate":
        if category:
            return _on_time_rate_by_category(category, year)
        if supplier_ids:
            return _on_time_rate_by_supplier_id(supplier_ids[0], year)

    if metric == "defect_rate" and category:
        return _defect_rate_by_category(category, year)

    if metric == "vendor_rating" and supplier_ids:
        return _vendor_rating_snapshot(supplier_ids[0], year)

    return None


def _yarn_otd_and_defect(period: str) -> TemplatedSQL:
    sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       s.country,
       vr.on_time_delivery_rate_pct,
       vr.quality_defect_rate_pct,
       vr.period
FROM suppliers s
JOIN vendor_rating vr ON s.supplier_id = vr.supplier_id
WHERE s.category_level_2 = 'Yarns'
  AND vr.period = ?
ORDER BY vr.on_time_delivery_rate_pct DESC
"""
    return TemplatedSQL(
        template_id="yarn_otd_defect_period",
        sql=sql.strip(),
        params=(period,),
        description=f"Yarn supplier OTD and defect rate for period {period}",
    )


def _avg_delay_above_threshold(threshold: float) -> TemplatedSQL:
    sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       s.category_level_2,
       s.risk_level,
       ROUND(AVG(d.delivery_delay_days), 2) AS avg_delay_days,
       COUNT(d.delivery_id) AS delivery_count
FROM suppliers s
JOIN delivery_events d ON s.supplier_id = d.supplier_id
GROUP BY s.supplier_id, s.supplier_name_anonymized, s.category_level_2, s.risk_level
HAVING avg_delay_days > ?
ORDER BY avg_delay_days DESC
"""
    return TemplatedSQL(
        template_id="avg_delay_above_threshold",
        sql=sql.strip(),
        params=(threshold,),
        description=f"Suppliers with average delivery delay above {threshold} days",
    )


def _spend_by_kraljic() -> TemplatedSQL:
    sql = """
SELECT kraljic_quadrant,
       COUNT(*) AS supplier_count,
       ROUND(SUM(annual_spend_eur), 2) AS total_spend_eur
FROM suppliers
GROUP BY kraljic_quadrant
ORDER BY total_spend_eur DESC
"""
    return TemplatedSQL(
        template_id="spend_by_kraljic",
        sql=sql.strip(),
        params=(),
        description="Annual spend aggregated by Kraljic quadrant",
    )


def _demo_as_of_date() -> str:
    try:
        from core.demo_constants import DEMO_CURRENT_DATE

        return DEMO_CURRENT_DATE
    except ImportError:
        return "2025-12-01"


def _certificates_expiring_soon(days: int) -> TemplatedSQL:
    sql = """
SELECT d.supplier_id,
       s.supplier_name_anonymized,
       d.document_type,
       d.expiry_date,
       d.document_status
FROM documents d
JOIN suppliers s ON d.supplier_id = s.supplier_id
WHERE d.expiry_date IS NOT NULL
  AND d.expiry_date BETWEEN date(?) AND date(?, '+' || ? || ' days')
ORDER BY d.expiry_date ASC
"""
    return TemplatedSQL(
        template_id="certificates_expiring_soon",
        sql=sql.strip(),
        params=(_demo_as_of_date(), _demo_as_of_date(), days),
        description=f"Certificates expiring within {days} days (demo as-of {_demo_as_of_date()})",
    )


def _strategic_vendor_rating_rank() -> TemplatedSQL:
    sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       s.category_level_2,
       vr.final_vendor_rating_score,
       vr.rating_class,
       vr.suggested_action
FROM suppliers s
JOIN vendor_rating vr ON s.supplier_id = vr.supplier_id
WHERE s.kraljic_quadrant = 'Strategic'
ORDER BY vr.final_vendor_rating_score DESC
"""
    return TemplatedSQL(
        template_id="strategic_vendor_rating_rank",
        sql=sql.strip(),
        params=(),
        description="Strategic suppliers ranked by vendor rating score",
    )


def _esg_below_threshold_missing_docs(threshold: float) -> TemplatedSQL:
    sql = """
SELECT e.supplier_id,
       s.supplier_name_anonymized,
       e.final_esg_score,
       e.missing_or_expired_documents,
       e.esg_risk_level,
       e.human_review_required
FROM esg_assessments e
JOIN suppliers s ON e.supplier_id = s.supplier_id
WHERE e.final_esg_score < ?
  AND e.missing_or_expired_documents = 1
ORDER BY e.final_esg_score ASC
"""
    return TemplatedSQL(
        template_id="esg_below_threshold_missing_docs",
        sql=sql.strip(),
        params=(threshold,),
        description=f"Suppliers with ESG score below {threshold} and missing/expired documents",
    )


def _supplier_status_snapshot(supplier_id: str) -> TemplatedSQL:
    sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       s.qualification_status,
       s.kraljic_quadrant,
       s.category_level_1,
       s.category_level_2,
       s.risk_level,
       s.next_review_date,
       COUNT(d.document_id) AS document_count,
       SUM(CASE WHEN d.document_status != 'Valid' THEN 1 ELSE 0 END) AS invalid_document_count
FROM suppliers s
LEFT JOIN documents d ON s.supplier_id = d.supplier_id
WHERE s.supplier_id = ?
GROUP BY s.supplier_id
"""
    return TemplatedSQL(
        template_id="supplier_status_snapshot",
        sql=sql.strip(),
        params=(supplier_id,),
        description=f"Qualification status snapshot for {supplier_id}",
    )


def _on_time_rate_by_category(category: str, year: Optional[str]) -> TemplatedSQL:
    if year:
        sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       ROUND(AVG(d.on_time_flag) * 100.0, 2) AS on_time_delivery_rate_pct,
       COUNT(d.delivery_id) AS delivery_count
FROM suppliers s
JOIN delivery_events d ON s.supplier_id = d.supplier_id
WHERE s.category_level_2 = ?
  AND strftime('%Y', d.actual_delivery_date) = ?
GROUP BY s.supplier_id, s.supplier_name_anonymized
ORDER BY on_time_delivery_rate_pct DESC
"""
        params = (category, year)
    else:
        sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       ROUND(AVG(d.on_time_flag) * 100.0, 2) AS on_time_delivery_rate_pct,
       COUNT(d.delivery_id) AS delivery_count
FROM suppliers s
JOIN delivery_events d ON s.supplier_id = d.supplier_id
WHERE s.category_level_2 = ?
GROUP BY s.supplier_id, s.supplier_name_anonymized
ORDER BY on_time_delivery_rate_pct DESC
"""
        params = (category,)
    return TemplatedSQL(
        template_id="otd_by_category",
        sql=sql.strip(),
        params=params,
        description=f"On-time delivery rate for category {category}",
    )


def _on_time_rate_by_supplier_id(supplier_id: str, year: Optional[str]) -> TemplatedSQL:
    if year:
        sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       ROUND(AVG(d.on_time_flag) * 100.0, 2) AS on_time_delivery_rate_pct,
       COUNT(d.delivery_id) AS delivery_count
FROM suppliers s
JOIN delivery_events d ON s.supplier_id = d.supplier_id
WHERE s.supplier_id = ?
  AND strftime('%Y', d.actual_delivery_date) = ?
GROUP BY s.supplier_id, s.supplier_name_anonymized
"""
        params = (supplier_id, year)
    else:
        sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       ROUND(AVG(d.on_time_flag) * 100.0, 2) AS on_time_delivery_rate_pct,
       COUNT(d.delivery_id) AS delivery_count
FROM suppliers s
JOIN delivery_events d ON s.supplier_id = d.supplier_id
WHERE s.supplier_id = ?
GROUP BY s.supplier_id, s.supplier_name_anonymized
"""
        params = (supplier_id,)
    return TemplatedSQL(
        template_id="otd_by_supplier_id",
        sql=sql.strip(),
        params=params,
        description=f"On-time delivery rate for {supplier_id}",
    )


def _defect_rate_by_category(category: str, year: Optional[str]) -> TemplatedSQL:
    sql = """
SELECT s.supplier_id,
       s.supplier_name_anonymized,
       ROUND(AVG(q.defect_rate) * 100.0, 2) AS quality_defect_rate_pct,
       COUNT(q.quality_event_id) AS quality_event_count
FROM suppliers s
JOIN quality_events q ON s.supplier_id = q.supplier_id
WHERE s.category_level_2 = ?
GROUP BY s.supplier_id, s.supplier_name_anonymized
ORDER BY quality_defect_rate_pct DESC
"""
    return TemplatedSQL(
        template_id="defect_rate_by_category",
        sql=sql.strip(),
        params=(category,),
        description=f"Quality defect rate for category {category}",
    )


def _vendor_rating_snapshot(supplier_id: str, year: Optional[str]) -> TemplatedSQL:
    period = year or "2025"
    sql = """
SELECT vr.supplier_id,
       s.supplier_name_anonymized,
       s.category_level_2,
       s.kraljic_quadrant,
       vr.period,
       vr.on_time_delivery_rate_pct,
       vr.average_delay_days,
       vr.quality_defect_rate_pct,
       vr.operational_score,
       vr.risk_inverse_score,
       vr.esg_score,
       vr.final_vendor_rating_score,
       vr.rating_class,
       vr.suggested_action
FROM vendor_rating vr
JOIN suppliers s ON vr.supplier_id = s.supplier_id
WHERE vr.supplier_id = ?
  AND vr.period = ?
"""
    return TemplatedSQL(
        template_id="vendor_rating_snapshot",
        sql=sql.strip(),
        params=(supplier_id, period),
        description=f"Vendor rating snapshot for {supplier_id}",
    )
