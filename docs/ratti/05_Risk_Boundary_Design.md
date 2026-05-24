# Risk & Boundary Design｜Ratti Supplier Lifecycle Copilot

## 1. Core Principle
This MVP is a **decision-support system**, not an autonomous procurement decision-maker.

AI can recommend:
- qualification checklist
- document gaps
- risk flags
- KPI interpretation
- next actions

AI cannot independently:
- approve a supplier
- blacklist a supplier
- change SAP supplier status
- sign a contract
- issue a purchase order
- make ESG/legal compliance final judgement

## 2. SQL Safety
Allowed: SELECT, WITH, aggregation, JOIN on whitelisted keys, LIMIT for broad queries.
Forbidden: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, COPY/EXPORT, non-whitelisted tables.

## 3. Field Whitelist
| Table | Allowed Fields |
|---|---|
| suppliers | supplier_id, anonymized name, country, category, Kraljic quadrant, status, annual spend, risk scores, review dates |
| category_rules | category, Kraljic quadrant, frequency, required documents, weights |
| documents | document type, status, expiry date, extraction confidence, manual validation flag |
| purchase_orders | PO ID, supplier ID, dates, quantity, amount, payment terms |
| delivery_events | delay days, on-time flag, issue type |
| quality_events | non-conformity type, severity, defect rate, corrective action flag |
| risk_events | risk type, likelihood, impact, recommended action |
| esg_assessments | E/S/G scores, ESG score, missing documents, review flag |
| vendor_rating | KPI scores, risk score, ESG score, final rating, suggested action |

## 4. Low-confidence Handling
If router confidence < 0.75:
1. Ask clarifying question if supplier/category/metric/time range is missing.
2. Use RAG fallback for general policy questions.
3. Avoid SQL generation if intent is unclear.
4. Return "I need more information" rather than guessing.

## 5. Human Confirmation Rules
Human approval is required for supplier status change, blacklist, audit confirmation, contract termination, supplier replacement, ESG/legal final judgement and high-risk actions.

## 6. Auditability
Every answer should include at least one of: SQL, source document/chunk, data scope, rule applied, confidence level, limitation.

## 7. Data Protection
Supplier names are anonymized. The dataset is synthetic and not a real Ratti supplier database. Broad data dump requests trigger clarification.
