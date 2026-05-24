"""Chinese routing and KPI template smoke tests."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from core.router_overrides import apply_lifecycle_router_overrides
from graph.nodes import _extract_supplier_id, _classify_risk_question
from tools.kpi_sql_builder import build_kpi_sql
from tools.sql_tools import run_sql_query_with_meta


class TestChineseLifecycleRouting(unittest.TestCase):
    def test_yarn_kpi_routes_and_sql(self):
        q = "展示2025年纱线供应商的准时交付率和缺陷率。"
        routed = apply_lifecycle_router_overrides({"intent": "kpi_query", "confidence": 0.5}, q)
        self.assertEqual(routed["intent"], "kpi_query")
        tpl = build_kpi_sql(q, {"metric": "other"})
        self.assertIsNotNone(tpl)
        self.assertEqual(tpl.template_id, "yarn_otd_defect_period")
        result = run_sql_query_with_meta(tpl.sql, params=tpl.params)
        self.assertGreater(result["meta"]["row_count"], 0)

    def test_vendor_rating_routes_and_sup_id(self):
        q = "为什么供应商SUP012获得了C级评级?"
        routed = apply_lifecycle_router_overrides({"intent": "kpi_query", "confidence": 0.5}, q)
        self.assertEqual(routed["intent"], "vendor_rating_explanation")
        self.assertEqual(_extract_supplier_id(q), "SUP012")

    def test_risk_review_routes(self):
        q = "本月应审查哪些供应商，因为风险较高？"
        routed = apply_lifecycle_router_overrides({"intent": "kpi_query", "confidence": 0.5}, q)
        self.assertEqual(routed["intent"], "risk_scenario")
        self.assertEqual(_classify_risk_question(q), "review_due")


if __name__ == "__main__":
    unittest.main()
