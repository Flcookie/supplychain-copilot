# 🏭 Supplier Lifecycle Copilot

***An AI-Powered Procurement Assistant for Supplier Qualification, KPIs, Risk & Vendor Rating — based on Ratti supplier management scenarios***

![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-orange)
![License](https://img.shields.io/badge/License-Apache%202.0-green)
![OpenAI](https://img.shields.io/badge/LLM-GPT--4%20%2F%20GPT--4o--mini-black)

---

## 🌐 Overview

**Supplier Lifecycle Copilot** extends the original SupplyChain Copilot with a **Ratti-inspired supplier management workflow**: qualification onboarding, policy Q&A, KPI NL2SQL, risk scenario analysis, and vendor rating explanation.

> Based on Politecnico di Milano × Ratti S.p.A. project logic (qualification flow, Kraljic segmentation, ESG scoring, vendor rating). Uses **anonymized synthetic data**, not real supplier records.

**RAG** handles unstructured policies (`policies_knowledge_base`). **NL2SQL** handles structured KPIs and supplier records in **`data/ratti_copilot_demo.db`** (anonymized synthetic Ratti demo data — no confidential supplier-level records).

See [`docs/ratti/`](docs/ratti/) for PRD, data dictionary, evaluation set, and risk boundary design.

### Core capabilities (interview demo)

1. **Supplier qualification checklist** — category path, Kraljic, required documents, human approval gates  
2. **Policy & ESG Q&A** — RAG over Ratti qualification / ESG / Kraljic policies  
3. **Supplier KPI query** — multi-metric NL2SQL (e.g. yarn OTD + defect rate in 2025)  
4. **Risk review & scenario analysis** — review-due lists with strict/relaxed fallback; what-if delay  
5. **Vendor rating explanation** — score breakdown, driver analysis, recommended buyer actions  

## 🏢 Business Context & Problem Statement

In large manufacturing and retail enterprises, **supply chain teams face fragmented data silos**:
- Policy documents stored in shared drives or SharePoint.
- KPI dashboards buried in BI tools.
- Risk assessments manually compiled from spreadsheets.

This project addresses a common pain point:
> "How can supply chain professionals instantly retrieve policies, compare supplier KPIs, and analyze potential risks — all in one conversational interface?"

Supplier Lifecycle Copilot bridges this gap with a unified **AI decision-support assistant** that understands both structured and unstructured enterprise data.

## 🖥️ User Interface Preview

<p align="center">
  <img src="https://github.com/Flcookie/supplychain-copilot/blob/main/assets/ui_screenshot.png" width="90%" alt="SupplyChain Copilot Streamlit UI Preview">
</p>

> **Figure:** Streamlit chat UI with **scenario templates**, router-driven **Current task** (intent + confidence), structured answers (Summary / Key Findings / Evidence / Limitations), and **collapsed** Evidence & Debug panels (SQL + router JSON).

---
## 🚀 Live Demo

Try it here: [supplychain-copilot.streamlit.app](https://supplychain-copilot.streamlit.app/)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://supplychain-copilot.streamlit.app/)
---
**SupplyChain Copilot** (now **Supplier Lifecycle Copilot**) is an enterprise-grade AI assistant integrating **policy documents**, **supplier lifecycle data**, and **risk simulations** into one intelligent system.
It allows procurement teams to **generate qualification checklists**, **query KPIs**, **retrieve policies**, **analyze risk scenarios**, and **explain vendor ratings** in **natural language**.

Built with **LangGraph**, **LangChain**, **Pinecone**, and **Streamlit**, this project demonstrates a **production-ready AI Copilot architecture** for real-world enterprise supply chain applications.

---

## 🎯 Project Goals

* Improve enterprise information accessibility across supply chain teams.
* Unify **structured (SQL)** and **unstructured (RAG)** data in one conversational interface.
* Reduce time spent searching dashboards or policy PDFs.
* Demonstrate **enterprise-level LLM workflow** design using LangGraph.

### 💎 Value Proposition

* Faster supplier intelligence and decision-making.
* Explainable answers with document and data citations.
* Scalable foundation for ERP & document system integration.

---

## 🧠 System Architecture

### 🔹 Layers

| Layer                    | Description                                                 |
| ------------------------ | ----------------------------------------------------------- |
| **Streamlit Chat UI**    | Bilingual UI · 6 scenario templates · router “Current task” · business answer + collapsed Evidence / Debug |
| **LangGraph Workflow**   | Router → Qualification / Policy / KPI / Risk / Vendor Rating / Hybrid → Answer |
| **RAG (Pinecone)**       | Retrieves Ratti policy chunks + legacy policy/contract/SOP docs |
| **SQL KPI Query Engine** | NL → SQL over `ratti_copilot_demo.db` (9 tables, read-only whitelist) |
| **Risk Node**            | Review lists, quality issues, what-if delay, blacklist HITL |
| **Vendor Rating Node**   | Explains A/B/C/D ratings with score breakdown and SQL evidence |

### 🔸 Workflow Diagram

```
[START]
   │
   ▼
 Router Node ──→ Qualification ──┐
   │                              │
   ├────────→ Policy QA ──────────┤
   ├────────→ KPI Node ───────────┤
   ├────────→ Risk Scenario ──────┤
   ├────────→ Vendor Rating ──────┤
   └────────→ Hybrid Node ────────┤
                                  ├──→ Answer → [END]
```

The router classifies each question into lifecycle intents: `qualification_checklist`, `policy_qa`, `kpi_query`, `risk_scenario`, `vendor_rating_explanation`, or `hybrid_query`.

---

## 📂 Project Structure

```
app/           → User interfaces (CLI + Streamlit)
core/          → Configuration, prompts, environment
graph/         → LangGraph state, nodes, workflow
rag/           → RAG retriever logic (Pinecone / Chroma)
tools/         → SQL tools, ingestion helpers
data/          → SQLite DB & documents
ingestion/     → Document ingestion & vectorstore builder
```

---

## ⚙️ Setup & Environment

### 🧩 Dependencies

```bash
uv sync
```

### 🌍 Environment Variables (`.env`)

```bash
OPENAI_API_KEY=sk-xxxx
INDEX_NAME=supply-copilot
PINECONE_API_KEY=pcsk_xxx
LANGSMITH_TRACING_V2=true
LANGSMITH_API_KEY=lsv2_xxx
LANGSMITH_PROJECT=supplychain-copilot

# Structured data (Ratti demo — default)
DB_URL=sqlite:///data/ratti_copilot_demo.db
SQLITE_DB_PATH=data/ratti_copilot_demo.db

# Fixed “business date” for review-due / certificate-expiry SQL (reproducible demos)
DEMO_CURRENT_DATE=2025-12-01
```

> **Note:** `data/ratti_copilot_demo.db` ships with the repo (from the Ratti lifecycle package). The legacy `data/supplychain_kpi.db` (`data/init_demo_db.py`) is the original 2-table KPI prototype and is **not** used by the current UI or graph.

### 🧭 Commands

```bash
# Install dependencies
uv sync

# Export Ratti policies → data/docs/policy/ (first-time or after policy edits)
uv run python ingestion/export_ratti_policies.py

# Build / rebuild Pinecone index (includes Ratti policy chunks)
uv run python -m ingestion.build_vectorstore --reindex

# Launch Streamlit UI (local)
uv run streamlit run app/ui.py --server.port 8502

# Ratti router eval (25 lifecycle questions)
uv run python -m eval.run_router_eval --dataset eval/datasets/ratti_eval_25.json --mode llm

# Ratti KPI SQL template smoke test (against ratti_copilot_demo.db)
uv run python -m eval.run_ratti_e2e_smoke
```

**Optional (legacy prototype only):**

```bash
uv run python -m data.init_demo_db   # creates data/supplychain_kpi.db — not used by default
```

---

## 💡 Key Innovations

| Feature | Description |
|----------|-------------|
| **Hybrid Reasoning** | Combines RAG for unstructured document retrieval with SQL for structured KPI data. |
| **LangGraph Workflow** | Router-based orchestration with ambiguity-first and confidence-second routing policy. |
| **Explainable Answers** | Each response now includes route decision (`intent/confidence/reason`) plus document or SQL evidence. |
| **Enterprise UI** | Streamlit-based dashboard showing intents, KPIs, and contextual citations. |
| **Scalable Integration** | Designed for integration with ERP and BI systems (PostgreSQL, SAP HANA, Snowflake). |

---

## 💬 Scenario Templates (recommended demo flow)

Use the sidebar **Scenario templates** in Streamlit, or paste these questions:

| # | Type | Example question | Router intent |
|---|------|------------------|---------------|
| 1 | **Qualification** | We have a new yarn supplier from China. What qualification process should we follow? | `qualification_checklist` |
| 2 | **KPI** | Show the on-time delivery rate and defect rate of yarn suppliers in 2025. | `kpi_query` |
| 3 | **Risk review** | Which suppliers should be reviewed this month due to high risk? | `risk_scenario` |
| 4 | **Vendor rating** | Why did supplier SUP012 receive a C rating? | `vendor_rating_explanation` |
| 5 | **Policy / ESG** | What ESG documents are required for yarn suppliers under Ratti qualification policy? | `policy_qa` |
| 6 | **Hybrid** | For strategic yarn suppliers, what monitoring policy applies and what was their average on-time delivery in 2025? | `hybrid_query` |

Answers follow a product-style structure where applicable: **Summary → Key Findings → Recommended Actions → Evidence → Limitations**. Technical detail (router JSON, raw SQL) sits under collapsed **Debug** / **Evidence** expanders.

---

## 🗄️ Data Design

### 🧱 Demo database (`ratti_copilot_demo.db`)

**Data snapshot label (shown in UI/evidence):** `anonymized Ratti demo database · ratti_copilot_demo.db`

Nine read-only whitelisted tables:

| Table | Role |
|-------|------|
| `suppliers` | Master data, Kraljic, risk level, review dates, qualification status |
| `category_rules` | Category-specific qualification rules |
| `documents` | Certificates & compliance docs (expiry) |
| `purchase_orders` | Order volume, amounts |
| `delivery_events` | On-time delivery / delay |
| `quality_events` | Defects, non-conformities |
| `risk_events` | Risk scores and events |
| `esg_assessments` | ESG scores |
| `vendor_rating` | A/B/C/D ratings and score components |

Calendar-sensitive queries (e.g. “review due this month”, certificates expiring soon) use **`DEMO_CURRENT_DATE`** (default `2025-12-01`) so demo results stay stable across real-world dates.

Full field definitions: [`docs/ratti/`](docs/ratti/) data dictionary.

### 🔗 Integration Guidelines

* Replace SQLite with **ERP/BI databases** (Postgres, MSSQL, SAP HANA, Snowflake).
* Use **read-only** connections; keep table allowlists and `LIMIT` guards as in `tools/sql_tools.py`.
* Point `DB_URL` / `SQLITE_DB_PATH` at your warehouse or replica.

---

## 🏢 Production Integration

### 📊 Structured supplier / KPI database

Connect to your enterprise data warehouse:

```bash
DB_URL=postgresql+psycopg2://readonly_user:password@host:5432/supplychain
```

### 📁 Document Sources

Replace `/data/docs` with your **corporate repository** (SharePoint, OneDrive, S3, NAS):

```python
metadata_example = {"department": "Procurement", "confidentiality": "internal"}
```

### 🔒 Access Control

```python
retriever = vectorstore.as_retriever(
    search_kwargs={"filter": {"department": current_user_dept}}
)
```

### 🧱 Security Principles

* Read-only database access
* No PII or financial data exposed
* Query audit logs (user, timestamp, intent, SQL, docs)
* Separate dev/staging/production environments

---

## 🧰 Technology Stack

| Component      | Technology                             |
| -------------- | -------------------------------------- |
| **Workflow**   | LangGraph                              |
| **RAG**        | LangChain + Pinecone                   |
| **LLM**        | OpenAI GPT-4 / GPT-4o-mini             |
| **Database**   | SQLite / SQLAlchemy / ERP Integration  |
| **UI**         | Streamlit                              |
| **Tracing**    | LangSmith                              |
| **Deployment** | uv · Docker · Streamlit Cloud · Vercel |

---

## 💡 Design Philosophy

> “Real enterprise AI is not about fancy prompts — it’s about integrating knowledge, data, and workflow.”

### Principles

* Each node = one clear responsibility.
* Combine structured SQL + unstructured text.
* Always provide explainable, cited answers.
* Modular, environment-driven design.
* Focus on **real business value** and workflow integration.

---

## Router Decision Policy

To avoid conflicting behavior between fallback and clarification, the router uses two independent signals:

1. `ambiguity_type`: whether user input is incomplete (`coreference`, `composite_intent`, `missing_entity`).
2. `confidence`: certainty of intent classification.

Decision priority:

- If `ambiguity_type` is not empty, trigger clarification first.
- Else if `confidence < 0.75`, trigger RAG fallback.
- Else route normally to lifecycle intents (`qualification_checklist`, `policy_qa`, `kpi_query`, `risk_scenario`, `vendor_rating_explanation`, `hybrid_query`).

This design separates two different failures:
- clarification solves missing/ambiguous input data;
- fallback solves uncertain intent classification.

---

## Evaluation Methodology

The repository now includes reproducible evaluation pipelines for both routing and RAG quality.

Router evaluation:
- Dataset: `eval/datasets/ratti_eval_25.json` (25 Ratti lifecycle questions)
- Legacy dataset: `eval/datasets/router_eval.json`
- Script: `eval/run_router_eval.py` (`--mode heuristic` or `--mode llm`)
- SQL smoke: `eval/run_ratti_e2e_smoke.py`
- Metrics: intent accuracy, ambiguity detection accuracy, clarification trigger rate, RAG fallback rate

RAG evaluation:
- Dataset: `eval/datasets/rag_eval.json` (60 samples — 30 policy_qa, 20 kpi_query, 10 hybrid)
- Script: `eval/run_rag_eval.py` (use `--skip-judge` to skip LLM-as-judge calls)
- Regression log generator: `eval/generate_regression_log.py` reads a judged JSON and refreshes `eval/REGRESSION.md` with low-score samples and root-cause hypotheses.
- Outputs: timestamped JSON + Markdown reports under `eval/results/`
- Metrics: Retrieval Recall@K, MRR, latency, faithfulness, citation precision, answer completeness, refusal accuracy

Latest retrieval comparison (judged):

| Run | Recall@5 | MRR | Faithfulness | Citation precision | Answer completeness | Refusal accuracy | Latency |
|-----|----------|------|---------------|--------------------|----------------------|-------------------|---------|
| `baseline` (vector-only) | 33.33% | 0.317 | n/a | n/a | n/a | n/a | 2945 ms |
| `post_hybrid` (hybrid + scenario chunkers) | 56.67% | 0.539 | n/a | n/a | n/a | n/a | 3677 ms |
| `judged_post_hybrid` (RRF + rerank=openai + KPI templates + hybrid intent) | 83.33% | 0.761 | 4.15 / 5 | 4.20 / 5 | 4.10 / 5 | 4.42 / 5 | 4908 ms |
| **`judged_final`** (router-narrow + refusal-path + dual-route hybrid + extended templates + structured policy prompt) | **100.00%** | **0.906** | **4.87 / 5** | **4.83 / 5** | **4.85 / 5** | **5.00 / 5** | 5898 ms |

Source files:
- Baseline: `eval/results/rag_eval_baseline_20260508_213656.md`
- Post-hybrid: `eval/results/rag_eval_post_hybrid_20260508_214658.md`
- Judged post-hybrid: `eval/results/rag_eval_judged_post_hybrid_20260508_223255.md`
- **Judged final: `eval/results/rag_eval_judged_final_20260508_230616.md`**
- Comparison: `eval/results/rag_eval_comparison_judged_final_20260508.md`

KPI SQL template usage in the legacy `supplychain_kpi.db` judged run (pre-Ratti schema):
- 14 / 20 KPI questions (70%) answered by deterministic SQL templates
- 3 / 20 fell back to LLM-generated SQL (1 self-repair attempt allowed)
- 3 / 20 returned a structured refusal where the metric was outside the **old** 2-table schema

**Ratti lifecycle** (`ratti_copilot_demo.db`): defect rate, ESG, vendor rating, and multi-metric yarn KPIs are supported via expanded templates — see `eval/run_ratti_e2e_smoke.py` and `tools/kpi_sql_builder.py`.

To re-run the full judged evaluation:

```bash
uv run python -m eval.run_rag_eval --label judged_final
uv run python -m eval.generate_regression_log \
    --report eval/results/rag_eval_judged_final_<TIMESTAMP>.json
```

---

## Experiment Boundaries

- Current benchmarks are offline simulation based on curated prompts and demo data.
- "Time reduction" claims are process decomposition estimates, not online telemetry.
- Demo data is clean and standardized; production rollout requires data quality assessment and governance.

---

## 🛠️ Roadmap

| Stage                                                | Status         |
| ---------------------------------------------------- | -------------- |
| Policy RAG + Pinecone                                | ✅ Done         |
| KPI Query via SQL                                    | ✅ Done         |
| Scenario Analysis Node                               | ✅ Done         |
| Bilingual Streamlit UI (EN / 中文)                    | ✅ Done         |
| Ratti lifecycle DB + 9-table NL2SQL                    | ✅ Done         |
| Qualification checklist + vendor rating nodes         | ✅ Done         |
| Product-style answer structure + collapsed Debug UI   | ✅ Done         |
| Evidence Contract (`core/evidence.py`)               | ✅ Done         |
| Hybrid Retrieval (RRF + rerank + scenario chunkers)  | ✅ Done         |
| Hybrid Intent Node (Policy + KPI joint answer)       | ✅ Done         |
| Deterministic KPI SQL templates                      | ✅ Done         |
| LLM-as-judge RAG evaluation pipeline                 | ✅ Done         |
| Regression Failure Log auto-population               | ✅ Done         |
| Chart Visualization                                  | 🔜 Planned     |
| Role-Based Access (RBAC)                             | 🔜 Planned     |
| ERP Database Integration                             | 🔜 In Progress |
| Dockerized Deployment                                | 🔜 Planned     |

---

## 🧾 Example Output (KPI)

**User:** Show the on-time delivery rate and defect rate of yarn suppliers in 2025.

**Copilot (structured excerpt):**

> **Answer Summary** — In 2025, 9 yarn suppliers were analyzed. Best OTD: Supplier_Yarns_IT_024 (91.7%, defect 3.82%). Weakest OTD: Supplier_Yarns_IT_048 (54.5%).  
> **Key Findings** — OTD range 54.5%–91.7%; most defect rates ~3–4%.  
> **Limitations** — Anonymized synthetic demo dataset; buyer validation required before supplier decisions.

**Evidence (collapsed in UI):** SQL executed · 9 rows · `anonymized Ratti demo database · ratti_copilot_demo.db`

---

## 👤 Author

**Beiran Ma (马贝然)**
*MSc Management Engineering — Supply Chain Track*
Politecnico di Milano

🎯 Focus: **AI × Supply Chain Systems**
🌐 [GitHub](https://github.com/flcookie) 

---

## ⚖️ License

**Apache 2.0 License**
[https://www.apache.org/licenses/LICENSE-2.0](https://www.apache.org/licenses/LICENSE-2.0)


