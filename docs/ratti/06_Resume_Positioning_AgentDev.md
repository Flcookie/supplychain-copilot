# Resume Positioning｜Agent 开发岗

> 面向 **Agent 开发 / LLM 应用工程师 / AI Engineer** 投递，弱化产品叙事，强化工作流工程、工具层、评测与可靠性。

## 一句话定位

独立完成企业采购场景的 LangGraph Agent：多意图路由 + 并行 Policy/KPI 分支聚合 + Hybrid RAG（双路召回→RRF→Cross-Encoder 精排）+ NL2SQL/MCP + Prompt Injection 防御 + RAGAS 式评测与语义缓存。路由（25 题）keyword 24% → heuristic+override 64% → LLM+override 100%；注入检测 100%（30 条攻防集，pytest 锁住）。

## 建议岗位关键词

Agent 开发 · LLM Application Engineer · AI Engineer · LangGraph / LangChain · RAG · Tool Calling · MCP · Eval · Prompt Injection · Observability

## 项目标题（简历用）

**Supplier Lifecycle Copilot｜基于 LangGraph 的企业采购 Agent 工作流｜独立完成**

## 推荐 Bullet（可直接贴简历）

- 基于 LangGraph 实现 Router + Qualification / Policy QA / KPI / Risk / Vendor Rating 多节点 Agent；对复合问题采用 **Policy ∥ KPI 并行分支 + Aggregate 聚合**，从线性单跳路由升级为可并行编排的工作流。
- 设计 ambiguity-first 的澄清与低置信兜底策略；在 25 条生命周期评测集上做可复现消融：keyword **24%** → heuristic 48% → 确定性 override 64% → LLM+override **100%**（归档 `router_eval_20260524_111249.json`）。离线档由 `pytest tests/test_offline_ablation.py` 锁住。
- 落地 **Hybrid RAG 工业漏斗**：Pinecone 向量 + BM25 → RRF Top20 → **bge-reranker CE Top5**；KPI 走 NL2SQL 模板 + **sqlglot AST 只读校验**；Policy QA **Prompt Injection** 30 条攻防集检测 **100%**（pytest 锁住）。
- 构建 **RAGAS 式** Policy QA 评测（Context Precision/Recall、Faithfulness、Answer Relevance），补齐相对 Router 的量化证据；并实现高频问题 **语义缓存** 降低重复 LLM 成本。
- 实现 MCP Server（policy / KPI 等工具），使 Agent 以 list_tools → call_tool 调用能力，解耦硬编码依赖；交付 Streamlit Demo、FastAPI 接口与可观测录制链路。

## 和「产品经理版」的差异

| 维度 | PM 版强调 | Agent 开发版强调 |
|------|-----------|------------------|
| 痛点 | buyer 效率、决策体验 | 路由失败、工具不可靠、注入攻击、不可评测 |
| 成果 | 场景覆盖、产品闭环 | StateGraph 并行编排、Tool、Guardrail、Eval、Cache |
| 指标 | 业务价值故事 | 路由准确率、注入拦截率、Faithfulness |
| 技术 | 一带而过 | LangGraph / RAG / NL2SQL / MCP / Injection / RAGAS |

## Agent 五维度对照（面试口述）

| 维度 | 本项目体现 |
|------|------------|
| 推理框架 | Router 多意图 + Hybrid 并行分支后聚合（非纯单跳） |
| 工具使用 | MCP query_policy / query_kpi + NL2SQL 白名单；RAG 漏斗含 CE 精排 |
| 记忆/状态 | SCState 结构化字段；语义缓存复用高频答案 |
| 安全与评估 | SQL 只读 + Injection 防御 + RAGAS/Router 评测集 |
| Agent 架构 | 条件边 + 并行 fan-out/join，而非单 Prompt |

## 面试边界说明（必说）

这不是 Ratti 正式实习。真实部分是校企项目中的采购流程、品类逻辑、准入与评分框架；供应商级记录与 PO 为脱敏/合成数据，用于验证 Agent 架构与评测。

## 技术栈速记

`Python · LangGraph · LangChain · OpenAI · Pinecone · BM25 · bge-reranker · SQLite · MCP · FastAPI · Streamlit · React · Pytest · LangSmith · Prompt Injection Guard · Semantic Cache`

## 评测命令速记

```bash
uv run python eval/run_injection_eval.py
uv run python eval/run_ragas_eval.py --limit 20
uv run python eval/run_router_eval.py
```

---

## 项目面经｜高频问答（Agent 开发岗）

> 用法：先背「一句话 + 边界说明」，再按模块抽问。回答尽量带**设计动机 → 怎么做 → 指标/取舍**三拍。

### 0. 开场与项目边界

**Q1. 用 1 分钟介绍这个项目。**  
A: 我做的是面向制造业采购的 Supplier Lifecycle Copilot。业务背景来自米兰理工 × Ratti 校企项目里的供应商准入、Kraljic、ESG、Vendor Rating 流程；数据是脱敏合成库，不是正式实习产出。技术上我用 LangGraph 搭多意图 Agent：Router 分流到准入清单、政策问答、KPI、风险、评级解释；复合问题走 Policy∥KPI 并行再聚合。检索是 Pinecone+BM25→RRF→bge-reranker 精排；结构化数据走 NL2SQL+白名单；工具经 MCP 暴露；并做了注入防御、RAGAS/路由评测和语义缓存。核心目标是企业场景下「可路由、可举证、可拦截、可评测」，而不只是能聊天。

**Q2. 这是真实业务还是 Demo？数据从哪来？**  
A: 流程与规则框架来自真实校企项目观察（准入、品类分层、ESG、评级维度是真的）；供应商主数据/PO 等是脱敏合成，用来验证架构与评测。面试里我会主动说清：这是独立扩展的工程原型，不是 Ratti 正式实习交付。

**Q3. 你在项目里具体负责什么？**  
A: 端到端独立完成：需求抽象、数据字典与评测集、LangGraph 工作流、RAG/NL2SQL/MCP、安全边界、评测脚本、Streamlit/FastAPI Demo，以及用 LangSmith Trace 迭代路由。

---

### 1. Agent 架构 / LangGraph

**Q4. 为什么用 LangGraph，而不是单 Prompt 或纯 LangChain Agent？**  
A: 采购问题是多意图、多工具、要分支的。单 Prompt 无法稳定区分「查政策 / 查 KPI / 要黑名单」且难单测。LangGraph 用 StateGraph + 条件边，把 Router、澄清、各任务节点、并行 Hybrid、Answer 拆开：状态显式（intent/confidence/ambiguity）、节点可替换可观测、失败可落在具体边。比黑盒 ReAct 更适合企业可控编排。

**Q5. 你的图长什么样？状态里有哪些关键字段？**  
A: `START→router→(clarification | rag_fallback | policy_qa | kpi | risk | vendor_rating | hybrid_dispatch)`；hybrid 是 `dispatch→(policy∥kpi)→aggregate→answer→END`。状态含 question、intent、confidence、ambiguity_type、retrieved_docs/citations/evidence、sql_*、policy/kpi_partial_answer、injection_scan 等。

**Q6. 和多 Agent 协作的关系？你做了并行吗？**  
A: 主路径仍是 Router 选一个专家节点；对「政策+KPI」复合问，升级为 Policy 与 KPI 两分支并行执行，再 Aggregate 合并——这是面经里常考的 fan-out/join，而不只是线性单跳。

**Q7. 低置信和歧义怎么处理？**  
A: ambiguity-first：有歧义先澄清；否则 confidence<0.75 走 RAG fallback，避免瞎生成 SQL。黑名单/改状态等要求 `human_approval_required`，AI 只给建议不自动落库。

---

### 2. Router

**Q8. Router 怎么设计的？准确率怎么来的？**  
A: LLM 输出结构化 JSON（intent/confidence/ambiguity/HITL/reason），再叠加确定性 override。25 题消融（可离线复现）：keyword 24% → heuristic 48% → override 64% → LLM+override 100%（归档）。面试说「规则兜底把下限抬起来，LLM 结构化输出把上限打满」，不要笼统说 65%→90%。

**Q9. 意图冲突或复合意图怎么办？**  
A: 清晰复合 → `hybrid_query` 并行；说不清先问「先看政策还是 KPI」；过宽「导出全部数据」标 `overbroad_data_request` 拒绝或澄清。

---

### 3. Hybrid RAG / 精排（高频八股）

**Q10. 为什么要 Hybrid Search？向量不够吗？**  
A: 向量擅长语义，弱于专有名词/编号/条款标题；BM25 擅长关键词。政策场景两者互补。我们双路召回后用 RRF 融合，减少「只靠向量漏掉关键条款」的情况。

**Q11. RRF 是什么？为什么不用简单加权平均？**  
A: Reciprocal Rank Fusion 按排名融合：`1/(k+rank)`，不依赖分数量纲对齐。向量距离和 BM25 分数不可比，RRF 更稳、实现简单，是多路召回常用融合。

**Q12. 为什么还要 Cross-Encoder 精排？和 Bi-Encoder 区别？**  
A: 召回阶段用双塔/向量便宜但粗；精排用 Cross-Encoder 把 (query, passage) 拼一起打相关性分，交互更充分，精度更高但贵，所以只对 RRF 后的 Top20 精排再取 Top5——标准缩窄漏斗。之前若只用 embedding 余弦重排，本质仍是 Bi-Encoder 近似，不如 CE。我们默认 `BAAI/bge-reranker-base`，中英政策都更合适。

**Q13. 完整检索漏斗说一遍。**  
A: 向量 Top~30 + BM25 Top~30 → 去重 RRF（+轻量 metadata boost）→ Top20 → bge-reranker Cross-Encoder → Top5 → 生成；metadata 里保留 rrf_rank、rerank_score、retrieval_funnel，方便 Trace 和面试展示。

**Q14. Chunk 怎么切的？**  
A: 按 doc_type 分场景 chunker（policy/contract/SOP/KPI 字典等），不是一刀切固定长度，保留章节标题进 metadata，利于召回与引用。

---

### 4. NL2SQL / 工具 / MCP

**Q15. KPI 为什么不全部塞进 RAG？**  
A: 数字必须可复算、可审计。非结构化走 RAG；指标走 NL2SQL/模板 SQL，答案回显 SQL 与行数。两套通道，减少「编造 OTD」幻觉。

**Q16. SQL 安全怎么做的？**  
A: sqlglot 解析 AST，失败则拒绝（fail-closed）。根节点只能是 SELECT/WITH；walk 拦截 Insert/Update/Delete/Drop；真实表名对表白名单，CTE 别名不算表；禁止 sqlite_master；自动补 LIMIT。不用正则匹配关键字。日历窗口绑 `DEMO_CURRENT_DATE`，不用 `date('now')`。写库动作走 HITL。

**Q17. 为什么引入 MCP？**  
A: 把 `query_policy` / `query_kpi` 收成标准工具，Agent 用 list_tools→call_tool，而不是节点里硬编码 import。便于扩展、隔离、和「工具目录参与路由」对齐行业形态。

---

### 5. 安全：Prompt Injection（必问）

**Q18. 政策问答如何防 Prompt Injection？**  
A: 三层：① 输入正则/规则扫描（忽略指令、扮演管理员、导出全部合同金额等），高危直接拒绝，不进检索；② System Prompt 声明用户内容为 untrusted，指令性语句不得覆盖角色；③ 输出侧敏感字段过滤兜底。30 条中英攻防集检测准确率 100%。和 SQL 白名单互补：一个防「话术越权」，一个防「查询越权」。

**Q19. 若攻击藏在检索到的文档里（间接注入）怎么办？**  
A: 当前重点防用户侧直接注入；间接注入可继续加强：检索内容也标 untrusted、生成端禁止执行文档中的指令、敏感操作仍走 HITL。会主动承认这是下一阶段加固点。

---

### 6. 评测与可观测

**Q20. 你怎么证明 RAG 没乱编？**  
A: Router 有意图准确率；RAG 用 RAGAS 式四维（Context Precision/Recall、Faithfulness、Answer Relevance）+ 既有 LLM judge；答案强制 Evidence（文档/SQL/局限）。Faithfulness 看主张是否被检索上下文支撑。

**Q21. LangSmith 怎么用的？**  
A: 对路由失败样本看 input/输出 JSON、走了哪条边、检索了什么；据此补 few-shot 和 override，而不是凭感觉改 prompt。

**Q22. 语义缓存怎么做？有什么坑？**  
A: 规范化问句精确命中 + embedding 相似度阈值；注入与澄清不缓存。坑：相似问句答案过期、多语言阈值要分语言桶——我们按 response_language 隔离，并设 TTL。

---

### 7. 产品边界与取舍

**Q23. AI 能不能直接拉黑供应商？**  
A: 不能。系统设计是决策支持：可给风险理由与建议，黑名单/改状态/准入审批必须人工确认（HITL）。

**Q24. 如果重做，你会优先改什么？**  
A: ① SQL 用 AST 解析加固白名单；② 间接 Prompt Injection；③ 多步 Tool-calling Agent Loop 做探索式分析；④ 精排做 A/B（CE on/off）量化 Recall@K / Faithfulness 提升。体现「知边界、有迭代 backlog」。

**Q25. 这个项目体现你对 Agent 岗位的理解？**  
A: Agent 不只是调 API，而是编排、工具契约、失败兜底、安全与评测。我用五维度对齐：推理（路由+并行聚合）、工具（MCP/RAG/SQL）、状态（SCState+缓存）、安全评估（注入+白名单+RAGAS）、架构（StateGraph 而非单 Prompt）。

---

### 8. 追问速答（30 秒版）

| 追问 | 一句答 |
|------|--------|
| Temperature？ | 任务节点 0，求稳不求花样。 |
| 为何 SQLite？ | Demo/评测可复现；生产可换仓，校验层可复用。 |
| 中英怎么支持？ | 路由 few-shot 双语 + override；回答按 response_language。 |
| 并行会不会重复计费？ | Hybrid 两分支各一次检索/生成，再用聚合；可用缓存与更小 partial prompt 控成本。 |
| Reranker 太重？ | 懒加载+单例；可 fallback openai/none；只对 Top20 跑 CE。 |
| 和 AutoGPT 类 Agent 比？ | 我们偏可控工作流，企业要审计与边界，不是无限自主循环。 |

### 9. 反问面试官（可选）

- 贵团队 Agent 更偏 LangGraph 工作流，还是开放式 Tool-calling Loop？
- 线上更关注 Faithfulness、延迟，还是工具调用成功率？
- 检索侧是否已有统一的「召回+精排」平台，还是业务自建？
