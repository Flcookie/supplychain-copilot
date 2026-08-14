# PRD 简版｜Ratti Supplier Lifecycle Copilot

## 1. Background / 背景
This MVP is based on the Politecnico di Milano × Ratti S.p.A. industry project context. Ratti is a high-end textile company with a complex supplier base across raw materials, outsourced processing, services, transportation, fixed assets and manufacturing. The current supplier qualification process is relatively manual, document-driven and not sufficiently differentiated by supplier category.

The product direction is to transform the project from a static process redesign into an interactive **Supplier Lifecycle Copilot** for buyers.

## 2. Target Users / 用户
| User | Need | Typical Question |
|---|---|---|
| Category Buyer | Check supplier qualification path and required documents | What documents are required for a new yarn supplier? |
| Procurement Manager | Monitor high-risk suppliers and review frequency | Which strategic suppliers need review this month? |
| Supplier Quality / ESG Role | Check certifications, ESG gaps and audit triggers | Which suppliers have expired certificates? |
| CPO / Procurement Lead | Understand vendor rating and risk exposure | Why did Supplier X receive a C rating? |

## 3. Pain Points / 痛点
1. Supplier qualification is manual and documentation-heavy.
2. Different supplier categories require different qualification intensity, but the current process is too standardized.
3. SAP supplier code exists, but supplier lifecycle status and category logic are not sufficiently visible.
4. ESG and traceability requirements are becoming more important in textile procurement.
5. Vendor rating is mainly operational and does not fully integrate risk and ESG dimensions.
6. Buyer needs explainable output, not a black-box answer.

## 4. Product Goals / 目标
| Goal | Metric |
|---|---|
| Reduce buyer effort in supplier onboarding | Generate qualification checklist within 1 conversation |
| Improve process consistency | Recommendations include category, Kraljic quadrant, required documents and next action |
| Improve explainability | Each answer shows data scope, SQL or document source when applicable |
| Support proactive supplier management | Identify high-risk / low-rating suppliers and suggest actions |
| Maintain governance | Human approval required for qualification status change, audit, blacklist and replacement |

## 5. Functional Scope / 功能范围
### In Scope
1. Qualification Assistant: generate category-based checklist, required documents, risk checks and next actions.
2. Policy QA: answer questions about qualification rules, ESG scoring, supplier code and Kraljic monitoring logic.
3. KPI Query via NL2SQL: query supplier OTD, delay, defect rate, spend, document expiry and rating data.
4. Risk Scenario Analysis: assess supplier delay, quality issue, missing certificate or single sourcing.
5. Vendor Rating Explanation: explain rating by operational performance, risk and ESG dimensions.
6. Supplier 360 View: aggregate basic info, qualification status, KPIs, risk, ESG and documents.

### Out of Scope / 非目标
1. No autonomous supplier approval.
2. No automatic blacklist decision.
3. No real SAP write-back in MVP.
4. No payment or contract execution.
5. No fully automated ESG/legal compliance judgement without human validation.
6. No procurement order placement.

## 6. MVP Success Criteria
- 25 evaluation questions can be routed to correct intent.
- NL2SQL queries are read-only and use whitelisted tables.
- Low-confidence or ambiguous questions trigger clarification.
- High-risk decisions include human-in-the-loop warning.
- Demo supports four scenarios: new supplier onboarding, KPI query, supplier review, risk scenario.
