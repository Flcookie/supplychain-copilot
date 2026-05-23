import json
import os
from typing import Any

from langchain_openai import ChatOpenAI


JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-4o")


def _safe_json_load(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def _judge_llm() -> ChatOpenAI:
    return ChatOpenAI(model=JUDGE_MODEL, temperature=0)


JUDGE_PROMPT = """You are an impartial evaluator for an enterprise supply-chain RAG system.

Evaluate the assistant answer against the user question, expected answer points, retrieved evidence, and answerability.
Return strict JSON only:
{{
  "faithfulness": {{"score": 1-5, "reason": "..."}},
  "citation_precision": {{"score": 1-5, "reason": "..."}},
  "answer_completeness": {{"score": 1-5, "reason": "..."}},
  "refusal_accuracy": {{"score": 1-5, "reason": "..."}}
}}

Rubric:
- faithfulness: 5 means every factual claim is supported by evidence; 1 means substantial unsupported or fabricated claims.
- citation_precision: 5 means cited sources/SQL directly support the answer; 1 means citations are irrelevant or missing.
- answer_completeness: 5 means all expected answer points are covered; 1 means most required points are missing.
- refusal_accuracy: if answerability=false, 5 means the answer clearly refuses or flags insufficient evidence; if answerability=true, 5 means it does not incorrectly refuse.

Question:
{question}

Expected answer points:
{expected_answer_points}

Answerability:
{answerability}

Retrieved evidence / Evidence Contract:
{evidence}

Assistant answer:
{answer}
"""


def judge_answer(
    *,
    question: str,
    expected_answer_points: list[str],
    answerability: bool,
    evidence: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    raw = _judge_llm().invoke(
        JUDGE_PROMPT.format(
            question=question,
            expected_answer_points=json.dumps(expected_answer_points, ensure_ascii=False),
            answerability=json.dumps(answerability),
            evidence=json.dumps(evidence, ensure_ascii=False),
            answer=answer,
        )
    ).content
    parsed = _safe_json_load(raw)
    return {
        key: {
            "score": int(parsed.get(key, {}).get("score", 0)),
            "reason": parsed.get(key, {}).get("reason", ""),
        }
        for key in ["faithfulness", "citation_precision", "answer_completeness", "refusal_accuracy"]
    }
