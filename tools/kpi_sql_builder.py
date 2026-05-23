"""Deterministic SQL templates for the KPIs we trust to build without LLM help.

The goal is to keep enterprise-critical metrics on a tested, parameterized path
and only fall back to the LLM when the question shape genuinely needs it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


SUPPLIER_SYNONYMS = {
    "alpha": "Alpha Electronics",
    "alpha electronics": "Alpha Electronics",
    "beta": "Beta Plastics",
    "beta plastics": "Beta Plastics",
    "gamma": "Gamma Metals",
    "gamma metals": "Gamma Metals",
    "delta": "Delta Packaging",
    "delta packaging": "Delta Packaging",
}

COUNTRY_HINTS = {
    "vietnam": "VN",
    "vietnamese": "VN",
    "vn": "VN",
    "china": "CN",
    "chinese": "CN",
    "cn": "CN",
    "germany": "DE",
    "german": "DE",
    "de": "DE",
}


_SUPPLIER_PATTERN = re.compile(
    r"alpha electronics|beta plastics|gamma metals|delta packaging|alpha|beta|gamma|delta",
    re.IGNORECASE,
)


@dataclass
class TemplatedSQL:
    template_id: str
    sql: str
    params: tuple
    description: str


def _detect_suppliers(text: str) -> list[str]:
    found = []
    for match in _SUPPLIER_PATTERN.findall(text or ""):
        canonical = SUPPLIER_SYNONYMS.get(match.lower())
        if canonical and canonical not in found:
            found.append(canonical)
    return found


def _detect_country(text: str) -> Optional[str]:
    lowered = (text or "").lower()
    for keyword, code in COUNTRY_HINTS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            return code
    return None


def _infer_metric_from_question(question: str) -> Optional[str]:
    text = (question or "").lower()
    if any(token in text for token in ["on-time", "on time", "ontime", "otd", "delivery rate", "delivery performance", "reliability"]):
        return "on_time_rate"
    if any(token in text for token in ["order volume", "purchase orders", "how many orders", "po count", "total orders", "order count"]):
        return "order_volume"
    if any(token in text for token in ["delay days", "average delay", "avg delay", "late by"]):
        return "avg_delay_days"
    return None


def build_kpi_sql(question: str, kpi_parse: dict) -> Optional[TemplatedSQL]:
    """Return a parameterized SQL for the question if a deterministic template applies."""

    metric = (kpi_parse or {}).get("metric") or "other"
    if metric in {"other", "comparison", "trend"}:
        inferred = _infer_metric_from_question(question)
        if inferred is not None:
            metric = inferred
    aggregation = (kpi_parse or {}).get("aggregation") or "other"
    suppliers = _detect_suppliers(f"{question} {kpi_parse.get('supplier_hint', '') or ''}")
    country = _detect_country(question)

    if metric == "on_time_rate":
        if aggregation in {"single_supplier", "other"} and len(suppliers) == 1:
            return _on_time_rate_single(suppliers[0])
        if aggregation in {"side_by_side", "rollup", "other"} and len(suppliers) >= 2:
            return _on_time_rate_side_by_side(suppliers)
        if country and not suppliers:
            return _on_time_rate_by_country(country)
        if aggregation == "rollup" and not suppliers:
            return _on_time_rate_ranking()

    if metric == "order_volume":
        if suppliers:
            return _order_volume_for_suppliers(suppliers)
        if country:
            return _order_volume_by_country(country)
        return _order_volume_ranking()

    if metric == "avg_delay_days":
        if len(suppliers) == 1:
            return _avg_delay_single(suppliers[0])
        if country:
            return _avg_delay_by_country(country)
        if not suppliers:
            return _avg_delay_overall()

    # Late-orders aggregations (kpi_013 "which country has more delayed orders",
    # kpi_020 "which materials are associated with late orders").
    text = (question or "").lower()
    if "delayed" in text or "late order" in text or "late orders" in text or "late delivery" in text:
        if "country" in text or "countries" in text or country:
            return _late_orders_by_country()
        if "material" in text or "materials" in text:
            return _late_orders_by_material()

    return None


def _on_time_rate_single(supplier: str) -> TemplatedSQL:
    sql = (
        "SELECT s.name AS supplier_name,\n"
        "       ROUND(SUM(CASE WHEN p.delivery_date <= p.due_date THEN 1 ELSE 0 END) * 1.0\n"
        "             / NULLIF(COUNT(p.id), 0), 4) AS on_time_rate,\n"
        "       COUNT(p.id) AS total_orders\n"
        "FROM suppliers s\n"
        "JOIN purchase_orders p ON p.supplier_id = s.id\n"
        "WHERE LOWER(s.name) LIKE LOWER(?)\n"
        "GROUP BY s.id, s.name"
    )
    return TemplatedSQL(
        template_id="otd_single_supplier",
        sql=sql,
        params=(f"%{supplier}%",),
        description=f"On-time delivery rate for {supplier}",
    )


def _on_time_rate_side_by_side(suppliers: list[str]) -> TemplatedSQL:
    placeholders = " OR ".join(["LOWER(s.name) LIKE LOWER(?)"] * len(suppliers))
    sql = (
        "SELECT s.name AS supplier_name,\n"
        "       ROUND(SUM(CASE WHEN p.delivery_date <= p.due_date THEN 1 ELSE 0 END) * 1.0\n"
        "             / NULLIF(COUNT(p.id), 0), 4) AS on_time_rate,\n"
        "       COUNT(p.id) AS total_orders\n"
        "FROM suppliers s\n"
        "JOIN purchase_orders p ON p.supplier_id = s.id\n"
        f"WHERE {placeholders}\n"
        "GROUP BY s.id, s.name\n"
        "ORDER BY on_time_rate DESC"
    )
    params = tuple(f"%{name}%" for name in suppliers)
    return TemplatedSQL(
        template_id="otd_side_by_side",
        sql=sql,
        params=params,
        description=f"On-time delivery rate side-by-side for {', '.join(suppliers)}",
    )


def _on_time_rate_by_country(country: str) -> TemplatedSQL:
    sql = (
        "SELECT s.name AS supplier_name,\n"
        "       ROUND(SUM(CASE WHEN p.delivery_date <= p.due_date THEN 1 ELSE 0 END) * 1.0\n"
        "             / NULLIF(COUNT(p.id), 0), 4) AS on_time_rate,\n"
        "       COUNT(p.id) AS total_orders\n"
        "FROM suppliers s\n"
        "JOIN purchase_orders p ON p.supplier_id = s.id\n"
        "WHERE s.country = ?\n"
        "GROUP BY s.id, s.name\n"
        "ORDER BY on_time_rate DESC"
    )
    return TemplatedSQL(
        template_id="otd_by_country",
        sql=sql,
        params=(country,),
        description=f"On-time delivery rate for suppliers in {country}",
    )


def _on_time_rate_ranking() -> TemplatedSQL:
    sql = (
        "SELECT s.name AS supplier_name,\n"
        "       ROUND(SUM(CASE WHEN p.delivery_date <= p.due_date THEN 1 ELSE 0 END) * 1.0\n"
        "             / NULLIF(COUNT(p.id), 0), 4) AS on_time_rate,\n"
        "       COUNT(p.id) AS total_orders\n"
        "FROM suppliers s\n"
        "JOIN purchase_orders p ON p.supplier_id = s.id\n"
        "GROUP BY s.id, s.name\n"
        "ORDER BY on_time_rate DESC"
    )
    return TemplatedSQL(
        template_id="otd_ranking",
        sql=sql,
        params=(),
        description="On-time delivery rate ranked across all suppliers",
    )


def _order_volume_for_suppliers(suppliers: list[str]) -> TemplatedSQL:
    placeholders = " OR ".join(["LOWER(s.name) LIKE LOWER(?)"] * len(suppliers))
    sql = (
        "SELECT s.name AS supplier_name,\n"
        "       COUNT(p.id) AS total_orders,\n"
        "       SUM(p.qty) AS total_qty\n"
        "FROM suppliers s\n"
        "JOIN purchase_orders p ON p.supplier_id = s.id\n"
        f"WHERE {placeholders}\n"
        "GROUP BY s.id, s.name\n"
        "ORDER BY total_orders DESC"
    )
    params = tuple(f"%{name}%" for name in suppliers)
    return TemplatedSQL(
        template_id="order_volume_supplier",
        sql=sql,
        params=params,
        description=f"Order volume for {', '.join(suppliers)}",
    )


def _order_volume_by_country(country: str) -> TemplatedSQL:
    sql = (
        "SELECT s.country,\n"
        "       COUNT(p.id) AS total_orders,\n"
        "       SUM(p.qty) AS total_qty\n"
        "FROM suppliers s\n"
        "JOIN purchase_orders p ON p.supplier_id = s.id\n"
        "WHERE s.country = ?\n"
        "GROUP BY s.country"
    )
    return TemplatedSQL(
        template_id="order_volume_country",
        sql=sql,
        params=(country,),
        description=f"Order volume aggregated by country = {country}",
    )


def _order_volume_ranking() -> TemplatedSQL:
    sql = (
        "SELECT s.name AS supplier_name,\n"
        "       COUNT(p.id) AS total_orders,\n"
        "       SUM(p.qty) AS total_qty\n"
        "FROM suppliers s\n"
        "JOIN purchase_orders p ON p.supplier_id = s.id\n"
        "GROUP BY s.id, s.name\n"
        "ORDER BY total_orders DESC"
    )
    return TemplatedSQL(
        template_id="order_volume_ranking",
        sql=sql,
        params=(),
        description="Order volume ranked across all suppliers",
    )


def _avg_delay_single(supplier: str) -> TemplatedSQL:
    sql = (
        "SELECT s.name AS supplier_name,\n"
        "       ROUND(AVG(julianday(p.delivery_date) - julianday(p.due_date)), 2) AS avg_delay_days,\n"
        "       COUNT(p.id) AS delayed_orders\n"
        "FROM suppliers s\n"
        "JOIN purchase_orders p ON p.supplier_id = s.id\n"
        "WHERE LOWER(s.name) LIKE LOWER(?)\n"
        "  AND p.delivery_date > p.due_date\n"
        "GROUP BY s.id, s.name"
    )
    return TemplatedSQL(
        template_id="avg_delay_single",
        sql=sql,
        params=(f"%{supplier}%",),
        description=f"Average delay days for {supplier}",
    )


def _avg_delay_overall() -> TemplatedSQL:
    sql = (
        "SELECT s.name AS supplier_name,\n"
        "       ROUND(AVG(julianday(p.delivery_date) - julianday(p.due_date)), 2) AS avg_delay_days,\n"
        "       COUNT(p.id) AS delayed_orders\n"
        "FROM suppliers s\n"
        "JOIN purchase_orders p ON p.supplier_id = s.id\n"
        "WHERE p.delivery_date > p.due_date\n"
        "GROUP BY s.id, s.name\n"
        "ORDER BY avg_delay_days DESC"
    )
    return TemplatedSQL(
        template_id="avg_delay_overall",
        sql=sql,
        params=(),
        description="Average delay days across suppliers (delayed POs only)",
    )


def _avg_delay_by_country(country: str) -> TemplatedSQL:
    sql = (
        "SELECT s.country,\n"
        "       ROUND(AVG(julianday(p.delivery_date) - julianday(p.due_date)), 2) AS avg_delay_days,\n"
        "       COUNT(p.id) AS delayed_orders\n"
        "FROM suppliers s\n"
        "JOIN purchase_orders p ON p.supplier_id = s.id\n"
        "WHERE s.country = ?\n"
        "  AND p.delivery_date > p.due_date\n"
        "GROUP BY s.country"
    )
    return TemplatedSQL(
        template_id="avg_delay_by_country",
        sql=sql,
        params=(country,),
        description=f"Average delay days for suppliers in {country} (delayed POs only)",
    )


def _late_orders_by_country() -> TemplatedSQL:
    sql = (
        "SELECT s.country,\n"
        "       SUM(CASE WHEN p.delivery_date > p.due_date THEN 1 ELSE 0 END) AS late_orders,\n"
        "       COUNT(p.id) AS total_orders\n"
        "FROM suppliers s\n"
        "JOIN purchase_orders p ON p.supplier_id = s.id\n"
        "GROUP BY s.country\n"
        "ORDER BY late_orders DESC"
    )
    return TemplatedSQL(
        template_id="late_orders_by_country",
        sql=sql,
        params=(),
        description="Late-order count grouped by supplier country",
    )


def _late_orders_by_material() -> TemplatedSQL:
    sql = (
        "SELECT p.material,\n"
        "       SUM(CASE WHEN p.delivery_date > p.due_date THEN 1 ELSE 0 END) AS late_orders,\n"
        "       COUNT(p.id) AS total_orders\n"
        "FROM purchase_orders p\n"
        "GROUP BY p.material\n"
        "HAVING late_orders > 0\n"
        "ORDER BY late_orders DESC"
    )
    return TemplatedSQL(
        template_id="late_orders_by_material",
        sql=sql,
        params=(),
        description="Late-order count grouped by material (only materials with late orders)",
    )
