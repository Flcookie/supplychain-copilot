"""AST SQL guard: fail-closed parse, SELECT-only, table allowlist, LIMIT."""

from __future__ import annotations

import pytest

from tools.kpi_sql_builder import build_kpi_sql
from tools.sql_guard import validate_read_only_sql
from tools.sql_tools import run_sql_query_with_meta


def test_select_allowlisted_table_gets_limit():
    sql = validate_read_only_sql("SELECT supplier_id FROM suppliers")
    assert "LIMIT" in sql.upper()
    assert "suppliers" in sql.lower()


def test_rejects_delete():
    with pytest.raises(ValueError, match="Only SELECT"):
        validate_read_only_sql("DELETE FROM suppliers")


def test_rejects_insert_and_update():
    with pytest.raises(ValueError, match="Only SELECT"):
        validate_read_only_sql("INSERT INTO suppliers (supplier_id) VALUES ('SUP999')")
    with pytest.raises(ValueError, match="Only SELECT"):
        validate_read_only_sql("UPDATE suppliers SET risk_level = 'Low'")


def test_rejects_multi_statement():
    with pytest.raises(ValueError, match="Exactly one"):
        validate_read_only_sql("SELECT 1; DROP TABLE suppliers")


def test_rejects_sqlite_master_via_union():
    with pytest.raises(ValueError, match="forbidden|allowlist"):
        validate_read_only_sql(
            "SELECT supplier_id FROM suppliers UNION SELECT sql FROM sqlite_master"
        )


def test_rejects_cte_that_reads_forbidden_table():
    with pytest.raises(ValueError, match="forbidden|allowlist"):
        validate_read_only_sql(
            "WITH x AS (SELECT * FROM sqlite_master) SELECT * FROM x"
        )


def test_allows_cte_over_allowlisted_tables():
    sql = validate_read_only_sql(
        "WITH x AS (SELECT supplier_id FROM suppliers) SELECT supplier_id FROM x"
    )
    rows = run_sql_query_with_meta(sql)["rows"]
    assert rows


def test_comment_cannot_hide_second_statement():
    with pytest.raises(ValueError):
        validate_read_only_sql("SELECT supplier_id FROM suppliers; /* */ DELETE FROM suppliers")


def test_placeholders_survive_rewrite():
    sql = validate_read_only_sql(
        "SELECT supplier_id FROM suppliers WHERE supplier_id = ? LIMIT 1"
    )
    result = run_sql_query_with_meta(sql, params=("SUP012",))
    assert result["meta"]["row_count"] == 1


def test_review_due_calendar_sql_is_parameterized():
    from core.demo_constants import DEMO_CURRENT_DATE

    sql = """
SELECT s.supplier_id, s.next_review_date
FROM suppliers s
WHERE s.next_review_date >= date(?, 'start of month')
  AND s.next_review_date < date(?, 'start of month', '+1 month')
"""
    validated = validate_read_only_sql(sql)
    assert "now" not in validated.lower()
    result = run_sql_query_with_meta(validated, params=(DEMO_CURRENT_DATE, DEMO_CURRENT_DATE))
    assert "row_count" in result["meta"]


def test_kpi_templates_still_execute():
    tpl = build_kpi_sql(
        "Show yarn supplier defect rate in 2025",
        {"metric": "defect_rate"},
    )
    assert tpl is not None
    result = run_sql_query_with_meta(tpl.sql, params=tpl.params)
    assert result["meta"]["row_count"] >= 1
    assert "strftime" in tpl.sql.lower()
    assert "2025" in tpl.params
