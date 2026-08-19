# Ablation card（可复现）

RAG 数字来自已入库的 `eval/results/*.json`。路由 heuristic / override 与注入检测由本脚本离线重算（不需要 API Key）。

## RAG 漏斗

| 阶段 | Recall@5 | MRR | Faithfulness | 产物 |
|------|----------|-----|--------------|------|
| Pinecone 单路向量 | 33.33% | 0.317 | n/a | `rag_eval_baseline_20260508_213656.json` |
| 向量 + BM25 → RRF | 56.67% | 0.539 | n/a | `rag_eval_post_hybrid_20260508_214658.json` |
| RRF + OpenAI embedding 精排 | 83.33% | 0.761 | 4.15 / 5 | `rag_eval_judged_post_hybrid_20260508_223255.json` |
| 完整漏斗 + 路由收窄 + 模板 SQL | 100.00% | 0.906 | 4.87 / 5 | `rag_eval_judged_final_20260508_230616.json` |

说明：归档 judged 跑分里的精排是 OpenAI embedding（bi-encoder）。当前默认漏斗是 RRF Top20 → **bge-reranker Cross-Encoder** Top5，由 `tests/test_rerank_funnel.py` 锁住漏斗契约。同池 CE vs Noop 夹具见 `eval/run_rerank_ablation.py`（live 对比需 `--live`）。

## 路由（`ratti_eval_25.json`，25 题）

| 模式 | Intent accuracy | 如何复现 |
|------|-----------------|----------|
| Keyword baseline | 24.00% | `uv run python -m eval.run_router_eval --mode heuristic` 中的 baseline |
| Heuristic lifecycle | 60.00% | `--mode heuristic` |
| Heuristic + deterministic override | 76.00% | `--mode override` |
| LLM + override（归档） | 100.00% | `eval/results/router_eval_20260524_111249.json`；重跑需 `--mode llm` |

## 路由 Held-out（`router_heldout.json`，10 条 paraphrase，不进 25 题）

| 模式 | Intent | Ambiguity | 产物 |
|------|--------|-----------|------|
| Heuristic + override | 70.00% | 100.00% | 离线重算 |
| LLM + override | 100.00% | 100.00% | `router_eval_20260819_162603.md` |

规则档 intent 仍是 70%（004/005/010 语义 paraphrase，不加 override）。
ambiguity 100%：`overbroad_data_request` / `coreference` 是生产路径上的确定性 gate，不是按 miss 写的 intent 规则。

`if` 子串误命中 `certificates` 已改为词边界匹配（`eval/run_router_eval.py::_has_keyword`），由 `tests/test_router_keyword_boundaries.py` 锁住。

## Prompt injection

- 检测准确率：**100%**（30 条中英攻防集）
- 离线复现：`uv run python eval/run_injection_eval.py` 或 `pytest tests/test_prompt_injection.py`

## 间接注入（检索文档，8 条）

- 用户问题保持 benign；chunk 含 ignore-previous / jailbreak 则丢弃，禁止条款（do not export all amounts）不丢。
- 离线复现：`pytest tests/test_indirect_injection.py`

## Cross-Encoder 同池消融（夹具）

- Noop 在 gold 排在 Top5 之外时 Recall@5=0；CE 式打分把它提到 Top1。
- 离线复现：`uv run python eval/run_rerank_ablation.py`；真模型对比需 `--live`。

