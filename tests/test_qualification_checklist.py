"""Tests for supplier qualification checklist routing and generation."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from core.qualification_rules import (
    apply_qualification_router_override,
    detect_qualification_checklist_intent,
    extract_qualification_input,
    format_checklist_markdown,
    generate_qualification_checklist,
    needs_category_clarification,
    normalize_qualification_input,
    resolve_response_language,
)


QUALIFICATION_TEST_QUESTIONS = [
    "We have a new yarn supplier from China. What qualification process should we follow?",
    "What documents are required for a chemical product supplier?",
    "A new logistics supplier wants to work with Ratti. What should the buyer check first?",
    "What should we do before creating an SAP code for a new supplier?",
    "Which documents are needed for an outsourced manufacturing supplier?",
    "What is the qualification process for a general service supplier?",
]

VAGUE_QUESTION = "What qualification process should we follow?"

ZH_YARN_QUESTION = "我们有一家来自中国的新纱线供应商，准入流程应该怎么走？"


class TestQualificationRouter(unittest.TestCase):
    def test_keyword_detection_on_sample_questions(self):
        for q in QUALIFICATION_TEST_QUESTIONS:
            with self.subTest(question=q):
                self.assertTrue(
                    detect_qualification_checklist_intent(q),
                    msg=f"Expected qualification keyword match: {q}",
                )

    def test_vague_question_still_routes_via_keywords(self):
        self.assertTrue(detect_qualification_checklist_intent(VAGUE_QUESTION))

    def test_router_override_from_policy_qa(self):
        parsed = apply_qualification_router_override(
            {"intent": "policy_qa", "confidence": 0.7, "reason": "default"},
            QUALIFICATION_TEST_QUESTIONS[0],
        )
        self.assertEqual(parsed["intent"], "qualification_checklist")
        self.assertGreaterEqual(parsed["confidence"], 0.9)


class TestQualificationExtraction(unittest.TestCase):
    def test_yarn_china_extraction(self):
        data = extract_qualification_input(QUALIFICATION_TEST_QUESTIONS[0])
        self.assertEqual(data["category_level_1"], "Goods")
        self.assertEqual(data["category_level_2"], "Yarns")
        self.assertEqual(data["country"], "China")
        self.assertFalse(needs_category_clarification(data))

    def test_vague_question_needs_clarification(self):
        data = extract_qualification_input(VAGUE_QUESTION)
        self.assertTrue(needs_category_clarification(data))

    def test_general_service_extraction(self):
        data = extract_qualification_input(QUALIFICATION_TEST_QUESTIONS[5])
        self.assertEqual(data["category_level_2"], "General Services")

    def test_resolve_language_from_chinese_question(self):
        self.assertEqual(resolve_response_language("en", ZH_YARN_QUESTION), "zh")
        self.assertEqual(resolve_response_language("zh", ZH_YARN_QUESTION), "zh")

    def test_chinese_yarn_supplier_extraction(self):
        data = extract_qualification_input(ZH_YARN_QUESTION)
        self.assertEqual(data["country"], "China")
        self.assertEqual(data["category_level_1"], "Goods")
        self.assertEqual(data["category_level_2"], "Yarns")
        self.assertEqual(data["provided_product_or_service"], "Yarns")
        self.assertFalse(needs_category_clarification(data))

    def test_chinese_yarn_normalized_defaults(self):
        data = normalize_qualification_input(extract_qualification_input(ZH_YARN_QUESTION))
        self.assertEqual(data["country"], "China")
        self.assertEqual(data["previous_relationship"], "New")
        self.assertEqual(data["risk_level"], "Unknown")


class TestQualificationChecklist(unittest.TestCase):
    def _checklist_for_question(self, question: str) -> dict:
        data = extract_qualification_input(question)
        self.assertFalse(needs_category_clarification(data), msg=question)
        return generate_qualification_checklist(data)

    def test_yarn_checklist_fields(self):
        result = self._checklist_for_question(QUALIFICATION_TEST_QUESTIONS[0])
        self.assertEqual(result["recommended_category"], "Goods > Yarns")
        self.assertIn("Strategic", result["kraljic_classification"])
        self.assertEqual(result["monitoring_frequency"], "Quarterly review")
        self.assertTrue(result["required_documents"])
        self.assertTrue(result["risk_checks"])
        self.assertTrue(result["next_action"])
        self.assertIn("Material traceability", " ".join(result["required_documents"]))

    def test_chinese_yarn_full_checklist(self):
        data = normalize_qualification_input(extract_qualification_input(ZH_YARN_QUESTION))
        self.assertFalse(needs_category_clarification(data))
        result = generate_qualification_checklist(data, lang="zh")
        md = format_checklist_markdown(result, lang="zh")
        self.assertEqual(result["recommended_category"], "商品 > 纱线")
        self.assertEqual(result["supplier_country"], "中国")
        self.assertEqual(result["kraljic_classification"], "战略类物料")
        self.assertEqual(result["monitoring_frequency"], "季度评审")
        self.assertIn("初步附条件合格", result["suggested_status"])
        self.assertIn("### 准入路径", md)
        self.assertIn("### 条件性文件 / 动作", md)
        self.assertIn("**推荐类别：**", md)
        self.assertNotIn("Recommended category", md)
        self.assertTrue(result["qualification_path"])
        self.assertTrue(result["required_documents"])
        self.assertTrue(result["risk_checks"])
        self.assertTrue(result["workflow_reminders"])
        self.assertTrue(result["next_action"])

    def test_chemical_checklist_documents(self):
        result = self._checklist_for_question(QUALIFICATION_TEST_QUESTIONS[1])
        docs = " ".join(result["required_documents"])
        self.assertIn("REACH", docs)
        self.assertIn("Safety Data Sheet", docs)

    def test_logistics_kraljic(self):
        result = self._checklist_for_question(QUALIFICATION_TEST_QUESTIONS[2])
        self.assertEqual(result["recommended_category"], "Transportation > Freight Transport / Logistics")
        self.assertIn("Leverage", result["kraljic_classification"])

    def test_sap_question_without_category_needs_clarification(self):
        data = extract_qualification_input(QUALIFICATION_TEST_QUESTIONS[3])
        self.assertTrue(needs_category_clarification(data))

    def test_categorized_samples_produce_checklist(self):
        categorized = [
            q for q in QUALIFICATION_TEST_QUESTIONS if q != QUALIFICATION_TEST_QUESTIONS[3]
        ]
        for q in categorized:
            with self.subTest(question=q):
                result = self._checklist_for_question(q)
                for key in (
                    "recommended_category",
                    "kraljic_classification",
                    "required_documents",
                    "risk_checks",
                    "next_action",
                ):
                    self.assertTrue(result.get(key), msg=f"missing {key} for {q}")


if __name__ == "__main__":
    unittest.main()
