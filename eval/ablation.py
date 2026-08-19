"""Frozen RAG metrics + live offline router/injection scores for the interview card."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "eval" / "results"
DATASETS = ROOT / "eval" / "datasets"

RAG_RUNS = (
    {
        "stage": "vector-only",
        "label": "Pinecone 单路向量",
        "file": "rag_eval_baseline_20260508_213656.json",
        "note": "无 BM25 / 无精排",
    },
    {
        "stage": "hybrid-rrf",
        "label": "向量 + BM25 → RRF",
        "file": "rag_eval_post_hybrid_20260508_214658.json",
        "note": "双路召回，未做 LLM judge",
    },
    {
        "stage": "hybrid-openai-rerank",
        "label": "RRF + OpenAI embedding 精排",
        "file": "rag_eval_judged_post_hybrid_20260508_223255.json",
        "note": "历史 judged 跑分；精排是 bi-encoder 而非 CE",
    },
    {
        "stage": "full-stack",
        "label": "完整漏斗 + 路由收窄 + 模板 SQL",
        "file": "rag_eval_judged_final_20260508_230616.json",
        "note": "当前架构基线；默认精排已切到 bge-reranker CE（见 tests/test_rerank_funnel.py）",
    },
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rag_ablation() -> list[dict]:
    rows = []
    for spec in RAG_RUNS:
        payload = _load_json(RESULTS / spec["file"])
        metrics = payload["metrics"]
        rows.append(
            {
                **spec,
                "recall_at_5": metrics["retrieval_recall_at_5"],
                "mrr": metrics["mrr"],
                "faithfulness": metrics.get("faithfulness"),
                "citation_precision": metrics.get("citation_precision"),
                "latency_ms": metrics.get("avg_latency_ms"),
            }
        )
    return rows


def router_ablation(dataset_path: Path | None = None) -> dict:
    from eval.run_router_eval import (
        baseline_router,
        evaluate,
        optimized_router,
        override_router,
    )

    path = dataset_path or (DATASETS / "ratti_eval_25.json")
    samples = _load_json(path)
    heldout = _load_json(DATASETS / "router_heldout.json")
    return {
        "dataset": str(path.relative_to(ROOT)).replace("\\", "/"),
        "samples": len(samples),
        "keyword_baseline": evaluate(baseline_router, samples),
        "heuristic": evaluate(optimized_router, samples),
        "heuristic_plus_override": evaluate(override_router, samples),
        "heldout_override": evaluate(override_router, heldout),
        "llm_plus_override_archived": {
            "source": "eval/results/router_eval_20260524_111249.json",
            "intent_accuracy": _load_json(RESULTS / "router_eval_20260524_111249.json")[
                "optimized"
            ]["intent_accuracy"],
        },
    }


def injection_ablation() -> dict:
    from core.prompt_injection import scan_user_input

    cases = _load_json(DATASETS / "prompt_injection_eval.json")
    correct = 0
    for case in cases:
        predicted = scan_user_input(case["question"]).should_refuse
        correct += int(predicted == bool(case["expect_refuse"]))
    n = len(cases)
    return {
        "dataset": "eval/datasets/prompt_injection_eval.json",
        "samples": n,
        "detector_accuracy": round(correct / n, 4) if n else 0.0,
        "source_archived": "eval/results/injection_eval_20260727_053637.json",
    }


def build_report() -> str:
    rag = rag_ablation()
    router = router_ablation()
    injection = injection_ablation()
    lines = [
        "# Ablation card（可复现）",
        "",
        "RAG 数字来自已入库的 `eval/results/*.json`。路由 heuristic / override 与注入检测由本脚本离线重算（不需要 API Key）。",
        "",
        "## RAG 漏斗",
        "",
        "| 阶段 | Recall@5 | MRR | Faithfulness | 产物 |",
        "|------|----------|-----|--------------|------|",
    ]
    for row in rag:
        faith = "n/a" if row["faithfulness"] is None else f"{row['faithfulness']:.2f} / 5"
        lines.append(
            f"| {row['label']} | {row['recall_at_5']:.2%} | {row['mrr']:.3f} | {faith} | `{row['file']}` |"
        )
    lines += [
        "",
        "说明：归档 judged 跑分里的精排是 OpenAI embedding（bi-encoder）。当前默认漏斗是 RRF Top20 → **bge-reranker Cross-Encoder** Top5，由 `tests/test_rerank_funnel.py` 锁住漏斗契约。同池 CE vs Noop 夹具见 `eval/run_rerank_ablation.py`（live 对比需 `--live`）。",
        "",
        "## 路由（`ratti_eval_25.json`，25 题）",
        "",
        "| 模式 | Intent accuracy | 如何复现 |",
        "|------|-----------------|----------|",
        f"| Keyword baseline | {router['keyword_baseline']['intent_accuracy']:.2%} | `uv run python -m eval.run_router_eval --mode heuristic` 中的 baseline |",
        f"| Heuristic lifecycle | {router['heuristic']['intent_accuracy']:.2%} | `--mode heuristic` |",
        f"| Heuristic + deterministic override | {router['heuristic_plus_override']['intent_accuracy']:.2%} | `--mode override` |",
        f"| LLM + override（归档） | {router['llm_plus_override_archived']['intent_accuracy']:.2%} | `{router['llm_plus_override_archived']['source']}`；重跑需 `--mode llm` |",
        "",
        "## 路由 Held-out（`router_heldout.json`，10 条 paraphrase，不进 25 题）",
        "",
        "| 模式 | Intent | Ambiguity | 产物 |",
        "|------|--------|-----------|------|",
        f"| Heuristic + override | {router['heldout_override']['intent_accuracy']:.2%} | {router['heldout_override']['ambiguity_accuracy']:.2%} | 离线重算 |",
        "| LLM + override | 100.00% | 100.00% | `router_eval_20260819_162603.md` |",
        "",
        "规则档 intent 仍是 70%（004/005/010 语义 paraphrase，不加 override）。",
        "ambiguity 100%：`overbroad_data_request` / `coreference` 是生产路径上的确定性 gate，不是按 miss 写的 intent 规则。",
        "",
        "`if` 子串误命中 `certificates` 已改为词边界匹配（`eval/run_router_eval.py::_has_keyword`），由 `tests/test_router_keyword_boundaries.py` 锁住。",
        "",
        "## Prompt injection",
        "",
        f"- 检测准确率：**{injection['detector_accuracy']:.0%}**（{injection['samples']} 条中英攻防集）",
        f"- 离线复现：`uv run python eval/run_injection_eval.py` 或 `pytest tests/test_prompt_injection.py`",
        "",
        "## 间接注入（检索文档，8 条）",
        "",
        "- 用户问题保持 benign；chunk 含 ignore-previous / jailbreak 则丢弃，禁止条款（do not export all amounts）不丢。",
        "- 离线复现：`pytest tests/test_indirect_injection.py`",
        "",
        "## Cross-Encoder 同池消融（夹具）",
        "",
        "- Noop 在 gold 排在 Top5 之外时 Recall@5=0；CE 式打分把它提到 Top1。",
        "- 离线复现：`uv run python eval/run_rerank_ablation.py`；真模型对比需 `--live`。",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    text = build_report()
    out = RESULTS.parent / "ABLATION.md"
    out.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"wrote {out}")
