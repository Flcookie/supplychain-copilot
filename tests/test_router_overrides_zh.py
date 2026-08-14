"""Chinese routing and KPI template smoke tests."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from core.router_overrides import apply_lifecycle_router_overrides
from core.entity_parse import classify_risk_question, extract_supplier_id
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
        self.assertEqual(extract_supplier_id(q), "SUP012")

    def test_vendor_rating_receive_tense(self):
        q = "Why did supplier SUP012 receive a C rating?"
        routed = apply_lifecycle_router_overrides(
            {"intent": "policy_qa", "confidence": 0.9, "ambiguity_type": "coreference"},
            q,
        )
        self.assertEqual(routed["intent"], "vendor_rating_explanation")
        self.assertIsNone(routed["ambiguity_type"])

    def test_coreference_cleared_when_supplier_id_present(self):
        q = "Why is TechFab Italia (SUP021) at high risk and what actions should we take?"
        routed = apply_lifecycle_router_overrides(
            {"intent": "risk_scenario", "confidence": 0.8, "ambiguity_type": "coreference"},
            q,
        )
        self.assertIsNone(routed["ambiguity_type"])

    def test_risk_review_routes(self):
        q = "本月应审查哪些供应商，因为风险较高？"
        routed = apply_lifecycle_router_overrides({"intent": "kpi_query", "confidence": 0.5}, q)
        self.assertEqual(routed["intent"], "risk_scenario")
        self.assertEqual(classify_risk_question(q), "review_due")

    def test_hybrid_policy_kpi_zh_not_swallowed_by_yarn_kpi(self):
        q = "战略纱线供应商需要哪些监控政策？他们在 2025 年的平均准时交付率是多少？"
        routed = apply_lifecycle_router_overrides({"intent": "kpi_query", "confidence": 0.95}, q)
        self.assertEqual(routed["intent"], "hybrid_query")

    def test_hybrid_policy_kpi_en(self):
        q = (
            "For strategic yarn suppliers, what monitoring policy applies "
            "and what was their average on-time delivery in 2025?"
        )
        routed = apply_lifecycle_router_overrides({"intent": "kpi_query", "confidence": 0.9}, q)
        self.assertEqual(routed["intent"], "hybrid_query")


if __name__ == "__main__":
    unittest.main()
