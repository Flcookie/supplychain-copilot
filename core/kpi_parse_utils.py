"""KPI parse post-processing shared by graph nodes."""

from tools.kpi_sql_builder import build_kpi_sql


def normalize_kpi_parse(question: str, kpi_parse: dict) -> dict:
    """Clear false-positive clarification when SQL templates can answer the question."""
    normalized = dict(kpi_parse or {})
    if build_kpi_sql(question, normalized) is not None:
        normalized["need_clarification"] = False
        normalized["clarification_reason"] = None
    text = (question or "").lower()
    raw = question or ""
    multi_tokens = [
        "defect",
        "缺陷",
        "on-time",
        "otd",
        "准时",
        "交付率",
        "delivery rate",
        "quality",
    ]
    if sum(1 for t in multi_tokens if t in text or t in raw) >= 2:
        normalized["need_clarification"] = False
        normalized["clarification_reason"] = None
        metrics = normalized.get("metrics") or []
        if not metrics:
            normalized["metrics"] = ["on_time_delivery_rate_pct", "quality_defect_rate_pct"]
    return normalized
