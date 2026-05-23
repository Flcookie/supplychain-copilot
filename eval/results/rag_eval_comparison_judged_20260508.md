# RAG Evaluation — Comparison Report (Judged)

This report compares retrieval and answer quality across three runs of
`eval/run_rag_eval.py` against the 60-sample `eval/datasets/rag_eval.json`
(30 policy_qa, 20 kpi_query, 10 hybrid).

| Run | Label | Recall@3 | Recall@5 | Recall@10 | MRR | Faithfulness | Citation precision | Answer completeness | Refusal accuracy | Avg latency |
|-----|-------|----------|----------|-----------|------|---------------|--------------------|----------------------|-------------------|-------------|
| 1 | `baseline` (vector-only, single retriever, llm-generated SQL) | 33.33% | 33.33% | 33.33% | 0.317 | n/a (skipped) | n/a (skipped) | n/a (skipped) | n/a (skipped) | 2944.96 ms |
| 2 | `post_hybrid` (hybrid retriever + scenario chunkers; LLM-as-judge skipped) | 56.67% | 56.67% | 56.67% | 0.539 | n/a (skipped) | n/a (skipped) | n/a (skipped) | n/a (skipped) | 3677.00 ms |
| 3 | `judged_post_hybrid` (RRF + token-overlap boost + rerank=openai + KPI template + hybrid intent + judged) | **83.33%** | **83.33%** | **83.33%** | **0.761** | **4.15 / 5** | **4.20 / 5** | **4.10 / 5** | **4.42 / 5** | 4908.39 ms |

Source artifacts:

- Run 1: `eval/results/rag_eval_baseline_20260508_213656.{md,json}`
- Run 2: `eval/results/rag_eval_post_hybrid_20260508_214658.{md,json}`
- Run 3: `eval/results/rag_eval_judged_post_hybrid_20260508_223255.{md,json}`

## Improvements landed between Run 2 and Run 3

1. **Router ambiguity fix.** Run 2 routed many general policy questions ("What
   are the qualification rules for new suppliers?") to the clarification node
   with `ambiguity_type=missing_entity`. The router prompt now explicitly says
   policy questions about general rules NEVER trigger missing_entity; we also
   added few-shot examples for those question shapes (`core/prompts.py:14`).
2. **Hybrid retrieval — RRF + metadata boost.** `rag/hybrid_retriever.py`
   replaced the linear weighted fusion with Reciprocal Rank Fusion across
   vector / keyword-rewrite / BM25 routes, and added a token-overlap
   `metadata_boost` that uses `section_title` (double-weighted), `doc_type`,
   `source_name`, and a filename-mention bonus. Default `vector_k=30`,
   `keyword_k=30`, rerank pool of 20.
3. **Rerank on by default.** `core/config.py` now defaults
   `RERANKER_BACKEND=openai`, so the OpenAI embedding reranker scores the top
   pool. `evidence.sources[*].rerank_score` is preserved for the UI.
4. **Doc-type-scoped retrievers.** `policy_qa_node` and the new `hybrid_node`
   filter to `policy / contract / sop / faq` (and `kpi_dict` for hybrid),
   keeping noisy KPI-only chunks out of policy retrieval.
5. **Hybrid intent.** A new `hybrid_query` intent and `hybrid_node` jointly run
   policy retrieval and a deterministic KPI SQL template (when one matches),
   merging both into a unified `Evidence` and a single answer with explicit
   "Policy expectation" / "KPI evidence" / "Conclusion" sections
   (`graph/nodes.py`, `graph/graph.py`).
6. **Deterministic KPI SQL templates.** `tools/kpi_sql_builder.py` covers
   `on_time_rate` (single supplier, side-by-side, by country, ranking),
   `order_volume` (per supplier, by country, ranking), and `avg_delay_days`
   (single supplier, overall). The LLM SQL path is now a fallback only.

## KPI template usage (Run 3)

| Intent | Samples | Template-built SQL | LLM-built SQL | No SQL run |
|--------|---------|--------------------|---------------|-------------|
| kpi_query | 20 | 11 (55%) | 3 (15%) | 6 (30% — mostly intentionally unanswerable kpi_011/017/018 + scenario-shaped kpi_007/013/020) |
| hybrid_query | 10 | 2 | 0 | 8 (template did not match the open-ended hybrid question) |

The 6 "no SQL run" KPI cases include the three intentionally unanswerable ones
(`kpi_011 defect_rate`, `kpi_017 OTIF`, `kpi_018 risk_score`) where the
correct behavior is to refuse — and refusal_accuracy is 4.42 / 5 globally,
confirming the system is doing this well.

## Remaining gaps (tracked in `eval/REGRESSION.md`)

14 of 60 samples are still flagged for human review. The mix of failure types:

- 10 retrieval failures (mostly hybrid samples where KPI evidence ranks lower
  than the matching contract clause; future work: weight policy + KPI sources
  separately when intent=hybrid_query).
- 4 judge-only failures (faithfulness / completeness 3 / 5) where the answer
  is on-topic but missed an expected sub-point (e.g. policy_004,
  policy_005). Those are typically prompt or chunk-granularity issues.

The regression log is regenerated on every judged run via
`uv run python -m eval.generate_regression_log --report <eval json>`.
