from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

GRAPH_BUILD_VERSION = "ratti-lifecycle-v3-product"


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def graph_cache_key() -> str:
    root = _project_root()
    watch_files = [
        os.path.join(root, "graph", "nodes.py"),
        os.path.join(root, "graph", "graph.py"),
        os.path.join(root, "core", "qualification_rules.py"),
        os.path.join(root, "core", "prompts.py"),
        os.path.join(root, "core", "router_overrides.py"),
        os.path.join(root, "core", "demo_constants.py"),
    ]
    mtimes = "|".join(str(os.path.getmtime(p)) for p in watch_files if os.path.exists(p))
    return f"{GRAPH_BUILD_VERSION}|{mtimes}"


@lru_cache(maxsize=4)
def get_graph(cache_key: str):
    from graph.graph import build_graph

    return build_graph()


def merge_clarification_reply(base_question: str, reply: str, lang_code: str) -> str:
    if lang_code == "zh":
        return f"{base_question.strip()}\n\n【用户补充】{reply.strip()}"
    return f"{base_question.strip()}\n\n[User clarification] {reply.strip()}"


def run_copilot(question: str, response_language: str) -> dict[str, Any]:
    active_graph = get_graph(graph_cache_key())
    result = active_graph.invoke(
        {"question": question, "response_language": response_language}
    )

    route_info = {
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "ambiguity_type": result.get("ambiguity_type"),
        "human_approval_required": result.get("human_approval_required"),
        "reason": result.get("reason"),
        "fallback_mode": result.get("fallback_mode", "none"),
        "kpi_parse": result.get("kpi_parse"),
    }

    return {
        "answer": result.get("answer", "No answer generated."),
        "intent": result.get("intent", "policy_qa"),
        "sources": result.get("retrieved_docs", []),
        "route_info": route_info,
        "citations": result.get("citations", []),
        "evidence": result.get("evidence", {}),
        "clarification_required": bool(result.get("ambiguity_type")),
    }
