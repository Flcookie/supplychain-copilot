from __future__ import annotations

import os
import time
import uuid
from functools import lru_cache
from typing import Any, Literal

GRAPH_BUILD_VERSION = "ratti-lifecycle-v6-hitl-approval"


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def graph_cache_key() -> str:
    root = _project_root()
    watch_files = [
        os.path.join(root, "graph", "nodes.py"),
        os.path.join(root, "graph", "graph.py"),
        os.path.join(root, "graph", "review.py"),
        os.path.join(root, "graph", "assessment.py"),
        os.path.join(root, "graph", "approval.py"),
        os.path.join(root, "graph", "checkpoint.py"),
        os.path.join(root, "core", "qualification_rules.py"),
        os.path.join(root, "core", "prompts.py"),
        os.path.join(root, "core", "router_overrides.py"),
        os.path.join(root, "core", "demo_constants.py"),
        os.path.join(root, "core", "prompt_injection.py"),
        os.path.join(root, "core", "semantic_cache.py"),
        os.path.join(root, "mcp_server", "server.py"),
        os.path.join(root, "mcp_server", "tools.py"),
        os.path.join(root, "app", "services", "mcp_client.py"),
    ]
    mtimes = "|".join(str(os.path.getmtime(p)) for p in watch_files if os.path.exists(p))
    backend = os.getenv("CHECKPOINT_BACKEND", "sqlite")
    return f"{GRAPH_BUILD_VERSION}|{backend}|{mtimes}"


@lru_cache(maxsize=4)
def get_graph(cache_key: str):
    from graph.graph import build_graph

    return build_graph()


def merge_clarification_reply(base_question: str, reply: str, lang_code: str) -> str:
    if lang_code == "zh":
        return f"{base_question.strip()}\n\n【用户补充】{reply.strip()}"
    return f"{base_question.strip()}\n\n[User clarification] {reply.strip()}"


def _thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def _interrupt_value(item: Any) -> Any:
    if item is None:
        return None
    if isinstance(item, dict):
        return item
    return getattr(item, "value", item)


def extract_interrupt_payload(result: dict[str, Any] | None = None, snap: Any = None) -> dict[str, Any] | None:
    raw = None
    if isinstance(result, dict):
        items = result.get("__interrupt__") or []
        if items:
            raw = _interrupt_value(items[0])
    if raw is None and snap is not None:
        interrupts = getattr(snap, "interrupts", None) or ()
        if not interrupts:
            for task in getattr(snap, "tasks", None) or ():
                interrupts = getattr(task, "interrupts", None) or ()
                if interrupts:
                    break
        if interrupts:
            raw = _interrupt_value(interrupts[0])
    if raw is None:
        return None
    return raw if isinstance(raw, dict) else {"value": raw}


def snapshot_is_paused(snap: Any) -> bool:
    if snap is None:
        return False
    if "approval" in list(snap.next or []):
        return True
    return extract_interrupt_payload(snap=snap) is not None


def _thread_is_paused(graph: Any, thread_id: str) -> bool:
    try:
        snap = graph.get_state(_thread_config(thread_id))
    except Exception:
        return False
    return snapshot_is_paused(snap)


def _enrich_paused_result(result: dict[str, Any], *, graph: Any, thread_id: str) -> dict[str, Any]:
    """Merge checkpoint values + interrupt payload when invoke stops at HITL."""
    snap = graph.get_state(_thread_config(thread_id))
    values = dict(snap.values or {})
    merged = dict(values)
    merged.update({k: v for k, v in result.items() if k != "__interrupt__" and v is not None})
    payload = extract_interrupt_payload(result, snap)
    merged["paused"] = True
    merged["interrupt"] = payload
    merged["human_approval_required"] = True
    merged["task_step"] = values.get("task_step") or "awaiting_approval"
    if payload:
        merged["proposed_action"] = payload.get("proposed_action") or merged.get("proposed_action")
        preview = payload.get("draft_preview")
        if not (merged.get("answer") or "").strip() and preview:
            merged["answer"] = preview
        if not (merged.get("answer") or "").strip():
            merged["answer"] = payload.get("message") or "Waiting for buyer approval."
    if not (merged.get("answer") or "").strip():
        merged["answer"] = "Assessment paused pending buyer approval."
    return merged


def _payload_from_result(
    result: dict[str, Any],
    *,
    thread_id: str,
    trace_id: str | None,
    cache_hit: bool = False,
) -> dict[str, Any]:
    route_info = {
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "ambiguity_type": result.get("ambiguity_type"),
        "human_approval_required": result.get("human_approval_required"),
        "reason": result.get("reason"),
        "fallback_mode": result.get("fallback_mode", "none"),
        "kpi_parse": result.get("kpi_parse"),
        "hybrid_parallel": bool(result.get("hybrid_parallel")),
        "injection_blocked": bool(result.get("injection_blocked")),
        "injection_scan": result.get("injection_scan"),
        "review_status": result.get("review_status"),
        "review_notes": result.get("review_notes"),
        "task_type": result.get("task_type"),
        "task_step": result.get("task_step"),
        "supplier_id": result.get("supplier_id"),
        "review_attempts": result.get("review_attempts"),
        "paused": bool(result.get("paused")),
        "proposed_action": result.get("proposed_action"),
        "approval_decision": result.get("approval_decision"),
    }
    interrupt_payload = result.get("interrupt")
    return {
        "answer": result.get("answer", "No answer generated."),
        "intent": result.get("intent", "policy_qa"),
        "sources": result.get("retrieved_docs", []),
        "route_info": route_info,
        "citations": result.get("citations", []),
        "evidence": result.get("evidence", {}),
        "clarification_required": bool(result.get("ambiguity_type")),
        "trace_id": trace_id,
        "thread_id": thread_id,
        "cache_hit": cache_hit,
        "policy_partial_answer": result.get("policy_partial_answer"),
        "kpi_partial_answer": result.get("kpi_partial_answer"),
        "review_status": result.get("review_status"),
        "task_plan": result.get("task_plan"),
        "supplier_id": result.get("supplier_id"),
        "paused": bool(result.get("paused")),
        "interrupt": interrupt_payload if isinstance(interrupt_payload, dict) else None,
        "approval_decision": result.get("approval_decision"),
        "proposed_action": result.get("proposed_action"),
    }


ForcedIntent = Literal[
    "hybrid_query",
    "qualification_checklist",
    "risk_scenario",
    "vendor_rating_explanation",
    "supplier_assessment",
]


def run_copilot(
    question: str,
    response_language: str,
    *,
    thread_id: str | None = None,
    task_type: Literal["chat", "supplier_assessment"] | None = None,
    supplier_id: str | None = None,
    forced_intent: ForcedIntent | None = None,
) -> dict[str, Any]:
    from core.prompt_injection import scan_user_input
    from core.semantic_cache import get_semantic_cache
    from observability.recorder import finish_trace, start_trace

    thread_id = thread_id or str(uuid.uuid4())
    cache = get_semantic_cache()
    scan = scan_user_input(question)
    # Checkpointed / forced-intent / multi-step tasks should not use semantic cache.
    use_cache = (
        not scan.should_refuse
        and task_type != "supplier_assessment"
        and forced_intent is None
        and not supplier_id
    )
    if use_cache:
        cached = cache.get(question, response_language)
        if cached is not None:
            cached = dict(cached)
            cached["thread_id"] = thread_id
            cached["cache_hit"] = True
            return cached

    active_graph = get_graph(graph_cache_key())
    trace_id = start_trace(question, response_language)
    started = time.perf_counter()

    initial: dict[str, Any] = {
        "question": question,
        "response_language": response_language,
        "thread_id": thread_id,
        "review_attempts": 0,
        "task_type": task_type or "chat",
    }
    if supplier_id:
        initial["supplier_id"] = supplier_id.upper()

    effective_intent = forced_intent
    if task_type == "supplier_assessment":
        effective_intent = "supplier_assessment"

    if effective_intent == "supplier_assessment":
        # Force assessment path: high-confidence router bypass via baseline-like seed.
        initial["intent"] = "supplier_assessment"
        initial["confidence"] = 0.99
        initial["ambiguity_type"] = None if supplier_id or _has_sup_id(question) else "missing_entity"
        initial["reason"] = "api supplier_assessment entry"
        initial["baseline_mode"] = True  # skip low-conf fallback; still honor assessment intent
        initial["task_type"] = "supplier_assessment"
    elif effective_intent:
        initial["intent"] = effective_intent
        initial["confidence"] = 0.99
        initial["ambiguity_type"] = None
        initial["reason"] = f"api forced_intent={effective_intent}"
        initial["baseline_mode"] = True

    # A paused HITL thread cannot accept a new invoke; fork so Approve stays on the old id.
    if _thread_is_paused(active_graph, thread_id):
        thread_id = str(uuid.uuid4())
        initial["thread_id"] = thread_id

    config = _thread_config(thread_id)
    try:
        result = active_graph.invoke(initial, config)
    except Exception as exc:
        finish_trace(
            trace_id,
            total_latency_ms=round((time.perf_counter() - started) * 1000, 2),
            error=str(exc),
        )
        raise

    if extract_interrupt_payload(result) or _thread_is_paused(active_graph, thread_id):
        result = _enrich_paused_result(result, graph=active_graph, thread_id=thread_id)

    answer = result.get("answer", "No answer generated.")
    finish_trace(
        trace_id,
        final_answer=answer,
        confidence=result.get("confidence"),
        intent=result.get("intent"),
        total_latency_ms=round((time.perf_counter() - started) * 1000, 2),
        ambiguity_type=result.get("ambiguity_type"),
        review_status=result.get("review_status"),
        human_approval_required=result.get("human_approval_required"),
    )

    payload = _payload_from_result(result, thread_id=thread_id, trace_id=trace_id)
    if use_cache and not payload["clarification_required"] and not payload.get("paused"):
        cache.put(question, response_language, payload)
    return payload


def run_supplier_assessment(
    supplier_id: str,
    response_language: str,
    *,
    question: str | None = None,
    thread_id: str | None = None,
) -> dict[str, Any]:
    sid = supplier_id.strip().upper()
    if response_language == "zh":
        default_q = f"请对供应商 {sid} 生成完整评估报告（档案、订单、KPI、适用政策与风险）。"
    else:
        default_q = (
            f"Run a full supplier assessment for {sid} covering profile, orders, "
            "KPIs, applicable policies, and risk signals."
        )
    return run_copilot(
        question or default_q,
        response_language,
        thread_id=thread_id,
        task_type="supplier_assessment",
        supplier_id=sid,
    )


def get_thread_history(thread_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """Replay checkpoint history for a thread (newest first)."""
    active_graph = get_graph(graph_cache_key())
    config = _thread_config(thread_id)
    history: list[dict[str, Any]] = []
    for i, snap in enumerate(active_graph.get_state_history(config)):
        if i >= limit:
            break
        values = snap.values or {}
        cfg = snap.config.get("configurable", {}) if isinstance(snap.config, dict) else {}
        history.append(
            {
                "thread_id": thread_id,
                "checkpoint_id": cfg.get("checkpoint_id"),
                "next": list(snap.next or []),
                "created_at": str(getattr(snap, "created_at", "") or ""),
                "intent": values.get("intent"),
                "task_step": values.get("task_step"),
                "review_status": values.get("review_status"),
                "supplier_id": values.get("supplier_id"),
                "answer_preview": (values.get("answer") or "")[:240],
                "question": values.get("question"),
            }
        )
    return history


def get_thread_state(thread_id: str) -> dict[str, Any]:
    active_graph = get_graph(graph_cache_key())
    snap = active_graph.get_state(_thread_config(thread_id))
    values = snap.values or {}
    cfg = snap.config.get("configurable", {}) if isinstance(snap.config, dict) else {}
    interrupt_payload = extract_interrupt_payload(snap=snap)
    paused = snapshot_is_paused(snap)
    return {
        "thread_id": thread_id,
        "checkpoint_id": cfg.get("checkpoint_id"),
        "next": list(snap.next or []),
        "paused": paused,
        "interrupt": interrupt_payload,
        "values": {
            "question": values.get("question"),
            "intent": values.get("intent"),
            "supplier_id": values.get("supplier_id"),
            "task_type": values.get("task_type"),
            "task_step": "awaiting_approval" if paused else values.get("task_step"),
            "task_plan": values.get("task_plan"),
            "review_status": values.get("review_status"),
            "review_notes": values.get("review_notes"),
            "answer": values.get("answer"),
            "citations": values.get("citations"),
            "evidence": values.get("evidence"),
            "human_approval_required": values.get("human_approval_required"),
            "proposed_action": (interrupt_payload or {}).get("proposed_action")
            if interrupt_payload
            else values.get("proposed_action"),
            "proposed_action_reasons": values.get("proposed_action_reasons")
            or (interrupt_payload or {}).get("reasons"),
            "approval_decision": values.get("approval_decision"),
            "approval_note": values.get("approval_note"),
        },
    }


def resume_thread(
    thread_id: str,
    *,
    approved: bool,
    note: str | None = None,
    response_language: str | None = None,
) -> dict[str, Any]:
    """Resume a graph paused at the approval interrupt. Does not write supplier data."""
    from langgraph.types import Command
    from observability.recorder import finish_trace, start_trace

    active_graph = get_graph(graph_cache_key())
    if not _thread_is_paused(active_graph, thread_id):
        snap = get_thread_state(thread_id)
        values = snap.get("values") or {}
        if values.get("approval_decision"):
            return _payload_from_result(
                {
                    **values,
                    "intent": values.get("intent") or "supplier_assessment",
                    "retrieved_docs": values.get("citations") or [],
                },
                thread_id=thread_id,
                trace_id=None,
            )
        raise ValueError(f"Thread {thread_id} is not waiting for approval.")

    trace_id = start_trace(f"resume:{thread_id}", response_language or "en")
    started = time.perf_counter()
    try:
        result = active_graph.invoke(
            Command(resume={"approved": approved, "note": note or ""}),
            _thread_config(thread_id),
        )
    except Exception as exc:
        finish_trace(
            trace_id,
            total_latency_ms=round((time.perf_counter() - started) * 1000, 2),
            error=str(exc),
        )
        raise

    if extract_interrupt_payload(result) or _thread_is_paused(active_graph, thread_id):
        result = _enrich_paused_result(result, graph=active_graph, thread_id=thread_id)

    finish_trace(
        trace_id,
        final_answer=result.get("answer"),
        confidence=result.get("confidence"),
        intent=result.get("intent"),
        total_latency_ms=round((time.perf_counter() - started) * 1000, 2),
        ambiguity_type=result.get("ambiguity_type"),
        review_status=result.get("review_status"),
        human_approval_required=result.get("human_approval_required"),
    )
    return _payload_from_result(result, thread_id=thread_id, trace_id=trace_id)


def _has_sup_id(text: str) -> bool:
    import re

    return bool(re.search(r"SUP\d{3}", text or "", re.IGNORECASE))
