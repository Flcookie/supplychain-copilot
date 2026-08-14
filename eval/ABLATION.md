# Ablation card（可复现）

RAG 数字来自已入库的 `eval/results/*.json`。路由 heuristic / override 与注入检测由本脚本离线重算（不需要 API Key）。

## RAG 漏斗

| 阶段 | Recall@5 | MRR | Faithfulness | 产物 |
|------|----------|-----|--------------|------|
| Pinecone 单路向量 | 33.33% | 0.317 | n/a | `rag_eval_baseline_20260508_213656.json` |
| 向量 + BM25 → RRF | 56.67% | 0.539 | n/a | `rag_eval_post_hybrid_20260508_214658.json` |
| RRF + OpenAI embedding 精排 | 83.33% | 0.761 | 4.15 / 5 | `rag_eval_judged_post_hybrid_20260508_223255.json` |
| 完整漏斗 + 路由收窄 + 模板 SQL | 100.00% | 0.906 | 4.87 / 5 | `rag_eval_judged_final_20260508_230616.json` |

说明：归档 judged 跑分里的精排是 OpenAI embedding（bi-encoder）。当前默认漏斗是 RRF Top20 → **bge-reranker Cross-Encoder** Top5，由 `tests/test_rerank_funnel.py` 锁住漏斗契约。

## 路由（`ratti_eval_25.json`，25 题）

| 模式 | Intent accuracy | 如何复现 |
|------|-----------------|----------|
| Keyword baseline | 24.00% | `uv run python -m eval.run_router_eval --mode heuristic` 中的 baseline |
| Heuristic lifecycle | 48.00% | `--mode heuristic` |
| Heuristic + deterministic override | 64.00% | `--mode override` |
| LLM + override（归档） | 100.00% | `eval/results/router_eval_20260524_111249.json`；重跑需 `--mode llm` |

## Prompt injection

- 检测准确率：**100%**（30 条中英攻防集）
- 离线复现：`uv run python eval/run_injection_eval.py` 或 `pytest tests/test_prompt_injection.py`

