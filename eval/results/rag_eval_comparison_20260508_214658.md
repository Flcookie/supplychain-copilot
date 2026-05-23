# RAG Evaluation Comparison

- Baseline: `eval/results/rag_eval_baseline_20260508_213656.json`
- Post-hybrid: `eval/results/rag_eval_post_hybrid_20260508_214658.json`
- Dataset: `eval/datasets/rag_eval.json`
- Samples: 60
- Judge mode: skipped for this run (`--skip-judge`)

## Metrics

| Metric | Baseline | Post-Hybrid | Delta |
| --- | ---: | ---: | ---: |
| Retrieval Recall@3 | 33.33% | 56.67% | +23.34 pp |
| Retrieval Recall@5 | 33.33% | 56.67% | +23.34 pp |
| Retrieval Recall@10 | 33.33% | 56.67% | +23.34 pp |
| MRR | 0.3167 | 0.5389 | +0.2222 |
| Avg latency | 2944.96 ms | 3677.00 ms | +732.04 ms |

## Interpretation

Hybrid retrieval improved source recall and ranking quality after adding structured demo documents, scenario-specific chunkers, local BM25 keyword search, metadata-aware fusion, and optional reranking.

Latency increased because each question now runs vector search plus keyword rewrite search and BM25 fusion. This is acceptable for the demo, but production should tune candidate counts and enable caching.

## Next Evaluation Step

Run a judged evaluation when API budget allows:

```bash
uv run python -m eval.run_rag_eval --label judged_post_hybrid
```
