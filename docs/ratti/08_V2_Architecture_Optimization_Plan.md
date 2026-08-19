# V2 架构优化方案｜Supplier Lifecycle Copilot

> 背景：对照「EchoMind」类技术点清单后，**没有照抄六个关键词**，而是把本项目已有半成品打通成工程闭环。
> 原则：**先核实代码里真实存在什么，再决定要不要做**。GPT 对初稿的收缩建议已采纳：不抽象万能 `@with_fallback`、不预设三路 Router、不扩 MCP 工具数量、不把 Monitor 说成自动学习。
> 关联文档：[00_README](00_README.md) 数据边界 · [07_Interview_QA_Playbook](07_Interview_QA_Playbook.md) 面试话术（本文写的是 **V2 已落地 + 明确不做**，07 文档里的 V1 数字仍然有效）。

**本轮已落地（克制版）**：线上指标聚合 + Badcase 导出、Held-out 路由集、KPI Groundedness / HITL Action Safety 规则评测、Pinecone→BM25 部分降级、Assessment Risk 复用 MCP `score_supplier_risk`。Held-out 上生产路径 LLM+override 已跑过：**intent 100% / ambiguity 100%**（`router_eval_20260819_162603.md`），对照纯规则档 70%。**Semantic Router 现在不做**——没有低置信误路由需要第三票。Session Memory、Query Rewrite、`query_supplier_profile` 仍等真实需求。

**续做（仍克制）**：间接注入（检索块 untrusted + 毒 chunk 丢弃）、同池 rerank 夹具、语义 paraphrase 另集 `router_heldout_semantic.json`、KPI 判据接到真实纱线 SQL。真 CE vs embedding 的 live 数字、session_context 仍不做。

---

## 一、现状核对表（先纠偏，再规划）

最初的口头分析是脱离代码写的，有几处和实际不符。逐条核实：

| 分析里的说法 | 代码里的实际情况 | 结论 |
|---|---|---|
| "Router 现在是 LLM + deterministic override，比较简陋" | `graph/nodes.py::router_node` 输出结构化 JSON，`core/router_overrides.py` 按优先级叠加确定性规则，25 题评测集从 24%→100%（见 07 文档 Q5） | override 不是"简陋兜底"，是刻意的分层设计。**第三路 embedding router 不预设要做**：先看 Monitor 里低置信占比，没有证据就不加复杂度 |
| "MCP 目前只有 query_policy / query_kpi 两个工具" | `mcp_server/tools.py` 实际有**三个**：`query_policy`、`query_kpi`、`score_supplier_risk` | **已修技术债**：`assessment_risk_branch` 改为调用 `score_supplier_risk_impl`，风险分数只有一个 Source of Truth。不追求再加 `query_supplier_profile` / Query Rewrite |
| "缺一个真正完整的 E2E 任务评测层" | `eval/judges.py::judge_answer` 已经是 4 维 LLM Judge，只覆盖 RAG/policy_qa | **已扩展规则判据**：`groundedness_kpi`（SQL 数值 vs 答案）和 `action_safety`（HITL 盖章），不把能确定性判断的事交给 LLM |
| "现在主要靠 LangSmith，监控是离线评估" | `observability/recorder.py` + `store.py` 已有节点级在线 trace | **已加聚合层**：`observability/metrics.py` 输出 router 分布 / clarification / HITL / review boost / P50·P95 / token。口径是 **线上观测 + Badcase 驱动迭代**，不是自动 adaptive routing |
| "三级记忆" | Checkpoint + 语义缓存都存在，但都不是"记忆" | **本轮不做**。没有用户系统，长期偏好没有落点；指代消解等出现真实多轮 case 再做 `session_context` |
| "优雅降级" | Reranker 三级降级、KPI repair-once 各自实现 | **没有强行做成一个 decorator**。统一的是观测口径 `core/resilience.py` 三类策略：Fallback / Retry-Repair / Partial Degradation；新增能力是 Pinecone 不可达 → BM25-only + 答案limitation |

**结论**：六个方向没有一个是"完全没有"。V2 做的是**打通、扩展、聚合**，不是新建一套系统。面试加分点是能分清"这是新功能"还是"把已有半成品做完整"。

---

## 二、优先级（已按 GPT 建议收缩）

| 优先级 | 做什么 | 本轮 |
|---|---|---|
| **P0** | Observability Metrics + Badcase Export | **已做** |
| **P0** | E2E Eval：KPI Groundedness + Action Safety | **已做** |
| **P0** | Resilience：统一观测 + Pinecone→BM25 | **已做** |
| **P1** | MCP Tool Contract 收敛（Risk Source of Truth） | **已做** |
| **P1** | Held-out Evaluation Set | **已做**（10 条 paraphrase，独立于 25 题） |
| **P1/P2** | Semantic Router | **不做**：Held-out LLM+override 已 100%，没有第三票要补的错误模式 |
| **P2** | Session Context | **有多轮指代 case 再做** |
| **不做** | CrewAI 式 Agent 协商 | 与采购场景的证据门控 / HITL 暂停点冲突 |
| **暂不做** | Long-term Memory / Query Rewrite / 再堆 MCP 工具 | 没用户系统；评测集里复合 rewrite 样本很少 |

不建议做的：**多 Agent 互相协商式编排（CrewAI 风格）**。当前 `Router → 专家节点 → Review → HITL → Answer` 是 workflow 式编排；改成对话式协商会让证据门控和 HITL 强制暂停难以保证。图拓扑 **未改**（`graph/graph.py`）。

---

## 三、P0 落地说明

### P0-1 线上观测 + Badcase 驱动迭代

**不要叫「动态 Monitor 闭环 / 自动学习」。** 实际链路是：

```
Trace → Metrics → Badcase 导出 → 人工标注 → 改 override/prompt → held-out 回归
```

1. `observability/metrics.py`：纯聚合，不改业务逻辑。指标：
   - `router_intent_distribution`（count + mean confidence）
   - `clarification_rate` / `hitl_trigger_rate` / `review_evidence_boost_rate`
   - `low_confidence_rate`（&lt; 0.75）
   - `p50_latency_ms` / `p95_latency_ms` / token totals
2. `traces` 表新增可空列：`ambiguity_type` / `review_status` / `human_approval_required`（`ALTER TABLE` 向后兼容）。`api/services/copilot.py` 在 `finish_trace` 时写入。
3. `eval/badcase_export.py`：导出 `error is not null` 或 `confidence < 0.75` 的 trace，人工标注后追加到 `eval/datasets/router_heldout.json`。
4. 配置改动约定：`core/router_overrides.py` 顶部注释 `# tuned from badcase batch YYYY-MM-DD`。

```bash
uv run python -m observability.metrics --all-time
uv run python -m eval.badcase_export
uv run python -m eval.run_router_eval --heldout --mode override
```

### P0-2 E2E Judge 扩展

能确定性判断的，不交给 LLM Judge。

- `judge_groundedness_kpi`：从 `sql_result` 抽数值，和答案做容差比对（相对 1% / 绝对 0.05，兼容百分数 vs 小数）。
- `judge_action_safety`：HITL 已决议必须出现 `graph/approval.py::_stamp` 盖章；未决议时禁止把「已拉黑 / 已写入」说成既成事实。
- `eval/run_e2e_eval.py` 离线跑 `eval/datasets/e2e_rule_cases.json`，产物 `eval/results/e2e_judged_<timestamp>.json`。
- `E2E Score = mean(适用判据)`；LLM RAG 分若混入则先 /5 归一化到 0–1。

### P0-3 Resilience（三类策略，不是一个 decorator）

```
Resilience（统一观测口径）
├─ Fallback          CE → Embedding → Noop          rag/rerank.py
├─ Retry / Repair    NL2SQL → Repair Once           graph/nodes.py kpi_node
└─ Partial Degradation  Pinecone Down → BM25 Only   rag/hybrid_retriever.py
```

`core/resilience.py::record_resilience_event` 把每次降级记进现有 trace（`kind=resilience`）。Pinecone 不可达时请求不 500：BM25-only 检索，证据 Contract 和答案末尾注明检索源受限。

---

## 四、P1：做了合同收敛，没做三路融合

### Router Fusion → 改为 Ablation / 可选

**没有实现 Semantic Router。** Held-out 证据已经够用：

| 档位 | Intent | Ambiguity | 产物 |
|---|---|---|---|
| override-only | 70% | **100%** | `router_eval_20260819_165517.md` |
| LLM+override（生产路径） | **100%** | **100%** | `router_eval_20260819_162603.md` |

规则档 intent 失手的是语义 paraphrase（`rated C`、ESG methodology、lapse/certificates），不是确定性 override 覆盖不到的另一类错误。生产路径 LLM 已经接住。007/009 是安全/澄清 gate 漏检（`export entire dataset`、dangling `them`），已补进 `apply_lifecycle_router_overrides`，规则档 ambiguity 从 80% 到 100%。`if`⊂`certificates` 是 matcher bug，已改成词边界，没有为此加 override。

再加 embedding 第三票的条件仍然是：Monitor 显示低置信误路由占比高 **且** 语义路由能补救。当前不满足（004/005/010 在 LLM+override 上已是 0 miss）。

### MCP：统一工具边界，不扩数量

`graph/assessment.py::assessment_risk_branch` 调用 `score_supplier_risk_impl`。返回值同时带加权分数和事件行，HITL 的 `human_review_required` 判定不受影响。Chat / Assessment / MCP 三处风险口径一致。

明确没做：`query_supplier_profile`、Query Rewrite。

---

## 五、P2（仍然谨慎）

Checkpoint + 语义缓存已经覆盖单 thread 连续性和重复问题。缺的是「接下来都看 Yarns、下一轮没提品类」。**没有用户系统就不做长期偏好。** 现有 `ambiguity_type: coreference` 先澄清（009 的 dangling `them` 已能拦住）；升级成 `session_context` 自动补全要等 Monitor 显示这类澄清被真实高频触发。

---

## 六、改动清单（实际落地）

```
新文件：
  observability/metrics.py
  eval/badcase_export.py
  eval/run_e2e_eval.py
  eval/datasets/e2e_rule_cases.json
  eval/datasets/router_heldout.json
  core/resilience.py
  tests/test_observability_metrics.py
  tests/test_e2e_judges.py
  tests/test_resilience_retrieval.py

改动文件：
  observability/store.py         +3 列迁移
  observability/recorder.py      finish_trace 透传新字段
  api/services/copilot.py        写入 ambiguity / review / HITL
  eval/judges.py                 groundedness_kpi / action_safety
  eval/run_router_eval.py        --heldout
  rag/hybrid_retriever.py        Pinecone 失败 → BM25-only
  rag/rerank.py                  fallback 记 resilience 事件
  graph/nodes.py                 router 埋点、SQL repair 观测、BM25 limitation
  graph/assessment.py            risk 复用 score_supplier_risk_impl
  mcp_server/tools.py            风险工具返回 events + 分数
  app/observability_ui.py        聚合指标条

不改：
  graph/graph.py 拓扑（router / review / approval 边）
  不新增 semantic_router.py
  不新增 @with_fallback 装饰器
```

---

## 七、面试一句话（可并入 07）

> V1 解决的是 Agent 能不能正确路由、检索、查数和做 HITL。V2 我没有继续堆 Agent，而是补工程闭环。首先把节点 Trace 聚合成 Router、Review、HITL、Latency 等线上指标；其次把 Badcase 导出进 Held-out 回归集——纯规则档 70%，生产路径 LLM+override 在同一份 10 题 paraphrase 上是 100%，所以现在没有上 Semantic Router 的证据；然后把评测从 Policy RAG 扩展到 KPI 数值 Grounding 和 HITL Action Safety；最后补了 Pinecone 故障时的 BM25 降级，并把 Risk 能力收敛到同一个 MCP Tool。三类恢复策略统一的是观测口径，不是一个万能 decorator。

---

## 八、风险提示 / 不要做的事

1. **不要为了六个技术点全部出现在简历上而全做**——Memory / 三路 Router 没有痛点时做了也讲不清「为什么需要」。
2. **不要把 Metrics 包装成系统自动学习**——讲成「人工看指标改配置」。
3. **不要让未来的语义路由覆盖确定性 override**——override 已经验证到 25 题 100%。
4. **数值判据必须用规则，不用 LLM**——和 NL2SQL 用 AST 而不是正则判断安全是同一原则反过来：能确定性判断的不交给模型猜。
