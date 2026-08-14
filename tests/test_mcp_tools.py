"""Unit tests for MCP tool implementations (no stdio / Pinecone required for KPI)."""

from __future__ import annotations

import pytest

from mcp_server.tools import ToolValidationError, query_kpi_impl


def test_query_kpi_rejects_empty_args():
    with pytest.raises(ToolValidationError, match="requires metric"):
        query_kpi_impl()


def test_query_kpi_rejects_bad_supplier_id():
    with pytest.raises(ToolValidationError, match="Invalid supplier_id"):
        query_kpi_impl(supplier_id="ABC", metric="on_time_rate")


def test_query_kpi_rejects_unknown_metric():
    with pytest.raises(ToolValidationError, match="Unsupported metric"):
        query_kpi_impl(metric="magic_score")


def test_query_kpi_rejects_non_select_sql():
    with pytest.raises(ToolValidationError, match="Only SELECT"):
        query_kpi_impl(sql="DELETE FROM suppliers")


def test_query_kpi_template_supplier_status():
    result = query_kpi_impl(
        supplier_id="SUP012",
        metric="supplier_status",
        question="What is the next step for SUP012?",
    )
    assert result["ok"] is True
    assert result["sql_source"] == "template"
    assert result["template_id"]
    assert isinstance(result["rows"], list)


def test_query_kpi_allowlisted_sql():
    result = query_kpi_impl(sql="SELECT supplier_id, risk_level FROM suppliers LIMIT 3")
    assert result["ok"] is True
    assert result["sql_source"] == "llm"
    assert len(result["rows"]) <= 3
