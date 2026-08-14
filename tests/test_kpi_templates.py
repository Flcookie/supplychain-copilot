"""KPI template year filters and demo as-of date (no LLM)."""

from __future__ import annotations

from core.demo_constants import DEMO_CURRENT_DATE
from tools.kpi_sql_builder import build_kpi_sql
from tools.sql_tools import run_sql_query_with_meta


def test_defect_rate_year_changes_result():
    q_2025 = "Show the defect rate of yarn suppliers in 2025"
    q_2026 = "Show the defect rate of yarn suppliers in 2026"
    t_2025 = build_kpi_sql(q_2025, {"metric": "defect_rate"})
    t_2026 = build_kpi_sql(q_2026, {"metric": "defect_rate"})
    assert t_2025 is not None and t_2026 is not None
    assert t_2025.params[-1] == "2025"
    assert t_2026.params[-1] == "2026"
    assert "strftime" in t_2025.sql
    rows_2025 = run_sql_query_with_meta(t_2025.sql, params=t_2025.params)["meta"]["row_count"]
    rows_2026 = run_sql_query_with_meta(t_2026.sql, params=t_2026.params)["meta"]["row_count"]
    assert rows_2025 != rows_2026


def test_otd_year_filter_present():
    tpl = build_kpi_sql(
        "Show on-time delivery rate of fabric suppliers in 2025",
        {"metric": "on_time_rate"},
    )
    assert tpl is not None
    assert tpl.template_id == "otd_by_category"
    assert "2025" in tpl.params
    assert "strftime" in tpl.sql


def test_certificates_use_demo_as_of_not_now():
    tpl = build_kpi_sql("Which certificates expire soon?", {"metric": "cert_expiry"})
    assert tpl is not None
    assert DEMO_CURRENT_DATE in tpl.params
    assert "now" not in tpl.sql.lower()
    result = run_sql_query_with_meta(tpl.sql, params=tpl.params)
    assert "executed_sql" in result["meta"]
    assert "now" not in result["meta"]["executed_sql"].lower()
