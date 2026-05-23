# RAG Evaluation — Final Comparison Report (Judged)

This report compares retrieval and answer quality across **four** runs of
`eval/run_rag_eval.py` against the 60-sample `eval/datasets/rag_eval.json`
(30 policy_qa, 20 kpi_query, 10 hybrid).

| Run | Label | Recall@5 | MRR | Faithfulness | Citation precision | Answer completeness | Refusal accuracy | Avg latency |
|-----|-------|----------|------|---------------|--------------------|----------------------|-------------------|-------------|
| 1 | `baseline` (vector-only, single retriever, llm-generated SQL) | 33.33% | 0.317 | n/a (skipped) | n/a (skipped) | n/a (skipped) | n/a (skipped) | 2945 ms |
| 2 | `post_hybrid` (hybrid retriever + scenario chunkers) | 56.67% | 0.539 | n/a (skipped) | n/a (skipped) | n/a (skipped) | n/a (skipped) | 3677 ms |
| 3 | `judged_post_hybrid` (RRF + rerank=openai + KPI template + hybrid intent + judged) | 83.33% | 0.761 | 4.15 / 5 | 4.20 / 5 | 4.10 / 5 | 4.42 / 5 | 4908 ms |
| 4 | **`judged_final`** (router-narrow + refusal-path + dual-route hybrid retrieval + extended KPI templates + structured policy prompt) | **100.00%** | **0.906** | **4.87 / 5** | **4.83 / 5** | **4.85 / 5** | **5.00 / 5** | 5898 ms |

Source artifacts:

- Run 1: `eval/results/rag_eval_baseline_20260508_213656.{md,json}`
- Run 2: `eval/results/rag_eval_post_hybrid_20260508_214658.{md,json}`
- Run 3: `eval/results/rag_eval_judged_post_hybrid_20260508_223255.{md,json}`
- Run 4: `eval/results/rag_eval_judged_final_20260508_230616.{md,json}`

## What changed between Run 3 and Run 4

The Run 3 audit surfaced 14 / 60 failures, dominated by **router over-triggering
`missing_entity` on answerable KPI / hybrid questions**. Run 4 closed those gaps:

1. **Router prompt narrowing.** `core/prompts.py`:
   - `missing_entity` is now explicitly forbidden for ranking, aggregation,
     country-scoped, hybrid-decision, and refusal-style questions. Default
     `ambiguity_type` is `null` unless a concrete reason exists.
   - Added 9 new few-shot examples covering these patterns.
2. **KPI refusal path.** `graph/nodes.py` introduces `_detect_unsupported_metric`
   which catches OTIF / defect_rate / risk_score / lead_time / first_pass_yield
   in the question and emits a structured Evidence-Contract refusal answer
   (`sql_source="refusal"`, no template fired) — instead of silently mapping
   OTIF to the OTD template (the kpi_017 bug from Run 3).
3. **Extended KPI SQL templates.** `tools/kpi_sql_builder.py` adds
   `late_orders_by_country`, `late_orders_by_material`, and
   `avg_delay_by_country`, plus stricter heuristic detection that now matches
   ranking and country-scoped questions even when the LLM parser returns
   `metric=other`.
4. **Dual-route hybrid retrieval.** `hybrid_node` runs two scoped retrievers
   (`policy/contract/sop/faq` k=5 and `kpi_dict` k=2) and **interleaves** them
   so at least one `metric_definitions.txt` chunk lands in the top-5 evidence
   list. This fixes hybrid_007 (Gamma Metals reliability) which previously
   returned only contract chunks for an unfamiliar supplier.
5. **Structured policy prompt.** `POLICY_QA_PROMPT` now requires a 3–5 bullet
   answer with inline section citations and an explicit "context does not cover
   X" line for sub-aspects that aren't in the documents. This lifted
   `answer_completeness` and `faithfulness` on policy questions.

## Failure breakdown across runs

| Run | Failures | Retrieval | Routing → clarification | Refusal misfire | Judge-only |
|-----|----------|-----------|--------------------------|------------------|-------------|
| 3 | 14 | 1 | 9 | 1 (kpi_017 OTIF wrong template) | 3 |
| 4 | 3 | 0 | 0 | 0 | 3 (all `policy_qa`, completeness 3 / faithfulness 3 on edge cases) |

Run 4 residuals are all in `eval/REGRESSION.md` for human follow-up:
- `policy_004` — answer_completeness 3 / 5 (incident escalation; minor sub-points missing)
- `policy_012` — answer_completeness 2 / 5 (non-strategic supplier approval; expected SOP retrieved at MRR 0.33)
- `policy_019` — citation_precision 3 / 5 (out-of-corpus question about employee travel; system correctly says insufficient evidence but cites supplier policy docs)

## KPI SQL template usage in Run 4

| Intent | Samples | Template-built SQL | LLM-built SQL | Refusal | No SQL run |
|--------|---------|--------------------|---------------|----------|-------------|
| kpi_query | 20 | **14 (70%)** | 3 (15%) | 3 (15%, all answerability=false samples — perfect refusal accuracy) | 0 |
| hybrid_query | 10 | 2 (20%) | 0 | 0 | 8 (open-ended composite questions; policy + kpi_dict retrieval still drives evidence) |

Compared with Run 3:

- KPI template hit-rate: **55% → 70%**
- KPI refusal correctness: 0/3 → 3/3 (the three intentionally-unanswerable
  samples now refuse instead of fabricating numbers)

## Acceptance criteria from `改进.md`

| Criterion | Target | Run 4 status |
|-----------|--------|---------------|
| Recall@5 | ≥ 85% | **100.00%** ✓ |
| Faithfulness | ≥ 4.5 / 5 | **4.87 / 5** ✓ |
| Citation precision | ≥ 4.5 / 5 | **4.83 / 5** ✓ |
| Answer completeness | ≥ 4.5 / 5 | **4.85 / 5** ✓ |
| Refusal accuracy | ≥ 4.5 / 5 | **5.00 / 5** ✓ |
| Hybrid composite-intent path | required | implemented (`hybrid_node` + dual retrieval) ✓ |
| Deterministic KPI SQL coverage | majority of common metrics | **70% of KPI samples + 100% of unsupported-metric refusals** ✓ |
| Regression failure log | populated from real eval | `eval/REGRESSION.md` auto-refreshed every judged run ✓ |
