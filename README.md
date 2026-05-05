# 🏭 SupplyChain Copilot

***An AI-Powered Enterprise Assistant for Supplier Management, Performance, and Risk Analysis***

![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-orange)
![License](https://img.shields.io/badge/License-Apache%202.0-green)
![OpenAI](https://img.shields.io/badge/LLM-GPT--4%20%2F%20GPT--4o--mini-black)

---

## 🌐 Overview
---

## 🏢 Business Context & Problem Statement

In large manufacturing and retail enterprises, **supply chain teams face fragmented data silos**:
- Policy documents stored in shared drives or SharePoint.
- KPI dashboards buried in BI tools.
- Risk assessments manually compiled from spreadsheets.

This project addresses a common pain point:
> "How can supply chain professionals instantly retrieve policies, compare supplier KPIs, and analyze potential risks — all in one conversational interface?"

SupplyChain Copilot bridges this gap with a unified **AI-powered assistant** that understands both structured and unstructured enterprise data.


## 🖥️ User Interface Preview

<p align="center">
  <img src="https://github.com/Flcookie/supplychain-copilot/blob/main/assets/ui_screenshot.png" width="90%" alt="SupplyChain Copilot Streamlit UI Preview">
</p>

> **Figure:** Streamlit-based enterprise dashboard integrating Chat + KPI + Policy + RAG sources.  
> Displays intent detection (Policy / KPI / Scenario), structured query results, and document citations in a unified conversational interface.

---
## 🚀 Live Demo

Try it here: [supplychain-copilot.streamlit.app](https://supplychain-copilot.streamlit.app/)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://supplychain-copilot.streamlit.app/)
---
**SupplyChain Copilot** is an enterprise-grade AI assistant integrating **policy documents**, **supplier performance data**, and **risk simulations** into one intelligent system.
It allows supply chain teams to **query KPIs**, **retrieve policies**, and **perform risk scenario analysis** in **natural language**.

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
| **Streamlit Chat UI**    | Interactive English UI with intent badges and citations     |
| **LangGraph Workflow**   | Router → Policy_QA → KPI → Scenario → Answer                |
| **RAG (Pinecone)**       | Retrieves supplier policies and management documents        |
| **SQL KPI Query Engine** | Translates natural language → SQL → English explanation     |
| **Scenario Node**        | Simulates “what-if” supplier risks & recommends mitigations |

### 🔸 Workflow Diagram

```
[START]
   │
   ▼
 Router Node ──→ Policy_QA Node ──┐
   │                              │
   ├────────→ KPI Node ───────────┤──→ Answer Node → [END]
   │                              │
   └────────→ Scenario Node ──────┘
```

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
KPI_DB_URL=sqlite:///data/supplychain_kpi.db
```

### 🧭 Commands

```bash
# Initialize demo KPI database
uv run python -m data.init_demo_db

# Ingest documents into Pinecone
uv run python -m ingestion.build_vectorstore

# Launch Streamlit UI
uv run streamlit run app/ui.py

# Run router A/B evaluation
uv run python -m eval.run_router_eval
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

## 💬 Example Queries

| Type           | Example Question                                           | Behavior                                                          |
| -------------- | ---------------------------------------------------------- | ----------------------------------------------------------------- |
| **Policy Q&A** | “How do we define a strategic supplier?”                   | Retrieves answer from policy docs *(green tag)*                   |
| **KPI Query**  | “What is the on-time delivery rate of Alpha Electronics?”  | Generates SQL → queries KPI DB → English explanation *(blue tag)* |
| **Comparison** | “Compare performance between Alpha and Beta suppliers.”    | Produces grouped SQL & compares results                           |
| **Scenario**   | “What happens if Vietnam suppliers are delayed by 7 days?” | Performs impact analysis & recommends mitigations *(orange tag)*  |

---

## 🗄️ Data Design

### 🧱 Database Schema

```sql
suppliers(
    id INTEGER PRIMARY KEY,
    name TEXT,
    country TEXT,
    is_strategic INTEGER
);

purchase_orders(
    id INTEGER PRIMARY KEY,
    supplier_id INTEGER,
    material TEXT,
    qty INTEGER,
    due_date TEXT,
    delivery_date TEXT
);
```

### 🔗 Integration Guidelines

* Replace SQLite with **ERP/BI databases** (Postgres, MSSQL, SAP HANA, Snowflake).
* Use **read-only** SQLAlchemy connections.
* Configure `KPI_DB_URL` in `.env`.

---

## 🏢 Production Integration

### 📊 KPI Database

Connect to your enterprise data warehouse:

```bash
KPI_DB_URL=postgresql+psycopg2://readonly_user:password@host:5432/supplychain
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
- Else route normally to `policy_qa`, `kpi_query`, or `scenario_analysis`.

This design separates two different failures:
- clarification solves missing/ambiguous input data;
- fallback solves uncertain intent classification.

---

## Evaluation Methodology

The repository now includes a reproducible router A/B evaluation pipeline:

- Dataset: `eval/datasets/router_eval.json`
- Script: `eval/run_router_eval.py`
- Outputs: timestamped JSON + Markdown reports under `eval/results/`

Tracked metrics:
- intent accuracy
- ambiguity detection accuracy
- clarification trigger rate
- RAG fallback rate

---

## Experiment Boundaries

- Current benchmarks are offline simulation based on curated prompts and demo data.
- "Time reduction" claims are process decomposition estimates, not online telemetry.
- Demo data is clean and standardized; production rollout requires data quality assessment and governance.

---

## 🛠️ Roadmap

| Stage                    | Status         |
| ------------------------ | -------------- |
| Policy RAG + Pinecone    | ✅ Done         |
| KPI Query via SQL        | ✅ Done         |
| Scenario Analysis Node   | ✅ Done         |
| English Streamlit UI     | ✅ Done         |
| Chart Visualization      | 🔜 Planned     |
| Role-Based Access (RBAC) | 🔜 Planned     |
| ERP Database Integration | 🔜 In Progress |
| Dockerized Deployment    | 🔜 Planned     |

---

## 🧾 Example Output

**User:** “Compare performance between Alpha and Beta suppliers.”
**Copilot Response:**

> Alpha Electronics has a higher on-time delivery rate (~90%) compared to Beta Plastics (~60%).
> This suggests Alpha is more reliable in meeting delivery commitments,
> while Beta shows more delays. Continuous supplier evaluation and corrective actions are recommended for Beta Plastics.

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


