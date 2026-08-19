# 供应商生命周期 Copilot（Supplier Lifecycle Copilot）

面向采购 / 供应链的对话式助手：供应商准入、政策问答、KPI 查询、风险场景与评级解释。

![LangGraph](https://img.shields.io/badge/LangGraph-工作流-blue)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![License](https://img.shields.io/badge/License-Apache%202.0-green)
![OpenAI](https://img.shields.io/badge/LLM-GPT--4%20%2F%20GPT--4o--mini-black)

---

## 项目简介

本项目基于 **米兰理工 × Ratti** 供应商管理场景抽象，用**脱敏合成数据**演示企业采购助手能力（非真实供应商机密数据）。

| 能力 | 说明 |
|------|------|
| 供应商准入清单 | 品类路径、Kraljic、所需证件、人工审批关口 |
| 政策 / ESG 问答 | RAG 检索资格认证、ESG、Kraljic 等政策文档 |
| 供应商 KPI 查询 | NL2SQL（准时率、缺陷率、支出等） |
| 风险复审与场景 | 复审清单、质量事件、延期 what-if |
| 评级解释 | A/B/C/D 构成拆解与采购建议 |

详细 PRD、数据字典与风险边界见 [`docs/ratti/`](docs/ratti/)。

---

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量（`.env`）

```bash
OPENAI_API_KEY=sk-xxxx
INDEX_NAME=supply-copilot
PINECONE_API_KEY=pcsk_xxx
LANGSMITH_TRACING_V2=true
LANGSMITH_API_KEY=lsv2_xxx
LANGSMITH_PROJECT=supplychain-copilot

# 结构化数据（Ratti 演示库，仓库已附带）
DB_URL=sqlite:///data/ratti_copilot_demo.db
SQLITE_DB_PATH=data/ratti_copilot_demo.db

# 复审/证件到期等「业务日期」（保证演示可复现）
DEMO_CURRENT_DATE=2025-12-01
```

### 3. （可选）重建向量索引

```bash
uv run python ingestion/export_ratti_policies.py
uv run python -m ingestion.build_vectorstore --reindex
```

### 4. 启动服务

| 入口 | 命令 | 地址 |
|------|------|------|
| FastAPI | `uv run uvicorn api.main:app --reload --port 8000` | http://127.0.0.1:8000 |
| Streamlit 对话 Copilot | `uv run streamlit run app/ui.py --server.port 8502` | http://127.0.0.1:8502 |
| 可观测性面板 | `uv run streamlit run app/observability_ui.py --server.port 8503` | http://127.0.0.1:8503 |
| React 工作台（开发） | `cd frontend && npm install && npm run dev` | http://localhost:5173 |

生产构建前端后，FastAPI 会自动托管 `frontend/dist`。

---

## 系统架构

```
用户提问
   │
   ▼
 Router（意图路由）
   ├─ 准入清单 qualification_checklist
   ├─ 政策问答 policy_qa
   ├─ KPI 查询 kpi_query
   ├─ 风险场景 risk_scenario
   ├─ 评级解释 vendor_rating_explanation
   ├─ 混合 hybrid_query（Policy ∥ KPI）
   └─ 供应商评估 supplier_assessment
          │  五路并行：profile / orders / kpi / policy / risk
          ▼
       Review（证据不足则补检索一次）
          │
          ├─ 普通结论 → Answer → END
          └─ 黑名单 / 改状态 → interrupt 暂停
                │  采购批准 / 驳回（不写库）
                ▼
              Answer → END
```

| 层级 | 说明 |
|------|------|
| UI | Streamlit 对话 · React 工作台 |
| 编排 | LangGraph：Router → 业务节点 → Review →（可选 HITL interrupt）→ Answer |
| RAG | Pinecone + BM25 → RRF → Cross-Encoder 重排 |
| SQL | 只读白名单 NL2SQL（`ratti_copilot_demo.db`） |
| 工具 | MCP / 本地实现（政策检索、KPI、风险评分等） |
| 观测 | LangSmith · 本地 Trace · `observability/metrics.py` 聚合 |

路由策略简述：输入不完整时先澄清；置信度不足时走 RAG 兜底；否则进入对应生命周期意图。供应商评估是**有状态、可暂停**的工作流：SqliteSaver checkpoint + 一次人工批准，不是无限 ReAct 循环。

演示这条故事：工作台打开 **SUP012** →「完整评估」→ 五路并行采集 → Review → 因「Qualified with Reserve」+ 需人工复核的风险事件而 `interrupt` → 刷新页面后点 **批准 / 驳回** 从同一 `thread_id` 恢复。Agent **不会**写供应商主数据。

---

## 推荐演示问题

| # | 类型 | 示例问题 | 意图 |
|---|------|----------|------|
| 1 | 准入 | 我们有一家中国新纱线供应商，应按什么资格流程办理？ | `qualification_checklist` |
| 2 | KPI | 展示 2025 年纱线供应商的准时交付率与缺陷率 | `kpi_query` |
| 3 | 风险 | 本月哪些高风险供应商需要复审？ | `risk_scenario` |
| 4 | 评级 | 为什么 SUP012 是 C 级？ | `vendor_rating_explanation` |
| 5 | 政策 | 纱线供应商按 Ratti 资格政策需要哪些 ESG 文件？ | `policy_qa` |
| 6 | 混合 | 战略纱线供应商的监控政策是什么？2025 平均准时率如何？ | `hybrid_query` |
| 7 | 评估 + HITL | 对 SUP012 做完整评估（工作台「完整评估」） | `supplier_assessment` → 暂停在批准关口 |

---

## 数据说明

演示库：`data/ratti_copilot_demo.db`（仓库内置，脱敏合成数据）。原始 CSV / Excel / 政策语料在 `data/ratti_source/`。

| 表 | 作用 |
|----|------|
| `suppliers` | 主数据、Kraljic、风险、复审日期、资格状态 |
| `category_rules` | 品类资格规则 |
| `documents` | 证件与合规材料（含到期） |
| `purchase_orders` | 订单量与金额 |
| `delivery_events` | 准时/延迟交付 |
| `quality_events` | 缺陷与不符合项 |
| `risk_events` | 风险事件与评分 |
| `esg_assessments` | ESG 评分 |
| `vendor_rating` | A/B/C/D 评级构成 |

日历类查询使用 `DEMO_CURRENT_DATE`（默认 `2025-12-01`），保证演示结果稳定。字段定义见 [`docs/ratti/`](docs/ratti/)。

---

## 目录结构

按运行入口 → Agent 核心 → 平台扩展 → 数据 / 评测 / 文档分层。根目录只保留配置与 README。

```
api/                    FastAPI
  main.py               应用入口（chat / workbench）
  routes/               HTTP 路由
  services/copilot.py   调用 LangGraph 的适配层
  schemas/              请求/响应模型

app/                    Streamlit 对话 UI、CLI、MCP 客户端
graph/                  LangGraph：state / nodes / 并行 hybrid / assessment / review / checkpoint
core/                   配置、提示词、路由 override、注入防护、语义缓存、Evidence
rag/                    Hybrid RAG：向量 + BM25 → RRF → Cross-Encoder
tools/                  Agent SQL：AST 只读校验、KPI 模板
mcp_server/             MCP 工具：query_policy / query_kpi / score_supplier_risk
observability/          本地 Trace + 指标聚合 + Badcase 导出
frontend/               React 采购工作台（Vite + TypeScript）
ingestion/              政策导出、分场景 chunker、向量索引构建

eval/                   评测脚本与数据集
  datasets/             路由 / RAG / 注入评测集
  results/              跑分报告
  helpers/              失败样本排查等一次性脚本
tests/                  Pytest

data/
  ratti_copilot_demo.db 运行用演示库
  ratti_source/         原始 CSV / Excel / 政策语料
  docs/                 已导出、供 RAG 使用的文本
docs/
  ratti/                PRD、数据字典、风险边界、简历定位
  notes/                迭代笔记
assets/portfolio/       作品集截图
scripts/                作品集 HTML 一次性生成脚本
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 工作流 | LangGraph |
| RAG | LangChain + Pinecone + BM25 + Cross-Encoder |
| LLM | OpenAI GPT-4 / GPT-4o-mini |
| SQL 安全 | sqlglot AST（只读 SELECT/WITH + 表白名单 + LIMIT） |
| API | FastAPI + Uvicorn |
| UI | Streamlit · React (Vite) |
| 工具协议 | MCP |
| 追踪 | LangSmith · 本地 Trace |

---

## 评测

口播卡（离线可复现，不需要 API Key）：

| 维度 | 数字 | 怎么锁住 |
|------|------|----------|
| RAG Recall@5 | 33.3% → 56.7% → 83.3% → **100%** | 冻结产物 `eval/results/rag_eval_*.json` |
| RAG MRR | 0.32 → 0.54 → 0.76 → **0.91** | 同上 |
| 路由 intent | keyword **24%** → heuristic 48% → override 64% → LLM+override **100%** | `uv run python -m eval.run_router_eval --mode override`；LLM 档见归档 JSON |
| 注入检测 | **30/30 = 100%** | `pytest tests/test_prompt_injection.py` |

完整表与产物路径：[`eval/ABLATION.md`](eval/ABLATION.md)（`uv run python eval/ablation.py` 重生成）。

说明：归档 RAG judged 跑分的精排是 OpenAI embedding；**当前默认**是 RRF Top20 → bge-reranker Cross-Encoder Top5。CE 漏斗契约由 `tests/test_rerank_funnel.py` 覆盖。

```bash
# 离线（CI 同款，无云密钥）
uv sync --group dev
uv run pytest tests -q
uv run python eval/ablation.py
uv run python eval/run_injection_eval.py
uv run python -m eval.run_router_eval --mode override
uv run python -m eval.run_router_eval --heldout --mode override
uv run python -m eval.run_e2e_eval

# 需要 LLM / Pinecone
uv run python -m eval.run_router_eval --mode llm
uv run python -m eval.run_ratti_e2e_smoke
uv run python -m eval.run_rag_eval --label judged_final
uv run python -m observability.metrics --all-time
```

NL2SQL 走 **sqlglot AST**：只允许单条 SELECT/WITH、表白名单、自动 LIMIT；解析失败则拒绝执行。

---

## 生产对接要点

- **结构化数据**：将 `DB_URL` / `SQLITE_DB_PATH` 指向只读仓（Postgres、SAP HANA、Snowflake 等），保留表白名单与 `LIMIT`。
- **文档**：用企业知识库替换 `data/docs`，检索侧可按部门 / 密级过滤。
- **安全**：只读库、**AST SQL 校验**（sqlglot）、Prompt Injection 扫描、HTTP 工具域名白名单、调用可审计。日历窗口使用 `DEMO_CURRENT_DATE`（默认 `2025-12-01`），不用 `date('now')`。
- **边界**：演示数据干净、标准化；上线需单独做数据质量与权限治理评估。

---

## 许可证

Apache License 2.0
