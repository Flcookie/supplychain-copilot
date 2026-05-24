# Prompt / Tool Design｜Ratti Supplier Lifecycle Copilot

## 1. Router Output Schema
```json
{
  "intent": "qualification_checklist | policy_qa | kpi_query | risk_scenario | vendor_rating_explanation | supplier_360 | ambiguous | unsafe_or_overbroad",
  "confidence": 0.0,
  "ambiguity_type": "missing_supplier_id | missing_category | missing_time_range | missing_metric | overbroad_data_request | none",
  "needs_clarification": true,
  "clarifying_question": "string",
  "selected_agent": "Qualification Assistant | Policy QA | KPI Query | Risk Scenario Analysis | Vendor Rating Explanation | Supplier 360 | Router Clarification",
  "required_tools": ["rag_retrieval", "sql_query", "rule_engine"],
  "risk_level": "low | medium | high",
  "human_approval_required": true
}
```

## 2. Qualification Assistant
Input: supplier description, country, category, known risk flags, uploaded documents.
Output: recommended category, Kraljic quadrant, qualification path, required documents, risk checks, suggested status, next action, evidence, human approval flag.

## 3. Policy QA
Input: natural language question + optional filters.
Tool: RAG retrieval over `policies_knowledge_base`.
Output: answer, citations, confidence, limitations.

## 4. KPI Query via NL2SQL
Input: question, whitelisted tables, optional supplier/category/time filter.
Tool: read-only SQL over SQLite.
Output: SQL, result table, data scope, summary, warnings.

## 5. Risk Scenario Analysis
Input: scenario, supplier/category, risk type.
Output: affected scope, risk interpretation, recommended actions, human approval flag, evidence.

## 6. Vendor Rating Explanation
Input: supplier_id and period.
Output: rating class, score breakdown, main reasons, suggested action.

## 7. Router Prompt Template
```text
You are the Router for a procurement AI Copilot. Classify the user's question into exactly one intent.
Return JSON only.

Rules:
- Required documents / onboarding / qualification path -> qualification_checklist.
- Process rules / Kraljic / ESG formula -> policy_qa.
- Numeric supplier KPI / ranking / spend / delay / defect / expiry -> kpi_query.
- What-if / risk impact / mitigation -> risk_scenario.
- Why rating changed / score formula -> vendor_rating_explanation.
- Approval, blacklist, audit, replacement -> human_approval_required=true.
- Missing supplier/category/time range -> needs_clarification=true.
```
