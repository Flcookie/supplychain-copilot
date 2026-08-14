"""In-process trace session: wraps LLM/SQL calls when a run is active."""

from __future__ import annotations

import inspect
import time
import uuid
from contextvars import ContextVar
from typing import Any

from observability.store import get_store

_active_trace_id: ContextVar[str | None] = ContextVar("active_trace_id", default=None)
_step_counter: ContextVar[int] = ContextVar("trace_step_counter", default=0)


def current_trace_id() -> str | None:
    return _active_trace_id.get()


def start_trace(
    query: str,
    response_language: str | None = None,
    agent_config_id: str | None = None,
    trace_id: str | None = None,
) -> str:
    """Begin a new trace; subsequent LLM/SQL calls auto-record as steps."""
    tid = trace_id or str(uuid.uuid4())
    get_store().create_trace(
        tid,
        query=query,
        response_language=response_language,
        agent_config_id=agent_config_id,
    )
    _active_trace_id.set(tid)
    _step_counter.set(0)
    return tid


def finish_trace(
    trace_id: str | None = None,
    *,
    final_answer: str | None = None,
    confidence: float | None = None,
    intent: str | None = None,
    total_latency_ms: float | None = None,
    error: str | None = None,
) -> None:
    tid = trace_id or _active_trace_id.get()
    if not tid:
        return
    get_store().finish_trace(
        tid,
        final_answer=final_answer,
        confidence=confidence,
        intent=intent,
        total_latency_ms=total_latency_ms,
        error=error,
    )
    if _active_trace_id.get() == tid:
        _active_trace_id.set(None)


def record_step(
    tool_called: str,
    *,
    tool_latency_ms: float | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    detail: dict[str, Any] | None = None,
) -> None:
    tid = _active_trace_id.get()
    if not tid:
        return
    step_num = _step_counter.get() + 1
    _step_counter.set(step_num)
    get_store().add_step(
        trace_id=tid,
        step_num=step_num,
        tool_called=tool_called,
        tool_latency_ms=tool_latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        detail=detail,
    )


def extract_token_usage(response: Any) -> tuple[int, int]:
    """Read prompt/completion tokens from LangChain AIMessage / OpenAI usage."""
    usage = getattr(response, "usage_metadata", None) or {}
    if isinstance(usage, dict) and usage:
        prompt = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        completion = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        if prompt or completion:
            return prompt, completion

    meta = getattr(response, "response_metadata", None) or {}
    if not isinstance(meta, dict):
        return 0, 0
    token_usage = meta.get("token_usage") or meta.get("usage") or {}
    if not isinstance(token_usage, dict):
        return 0, 0
    prompt = int(token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0)
    completion = int(
        token_usage.get("completion_tokens") or token_usage.get("output_tokens") or 0
    )
    return prompt, completion


def _caller_step_name(default: str = "llm") -> str:
    """Infer step label from the calling node function (e.g. router_node)."""
    for frame in inspect.stack()[2:8]:
        name = frame.function
        if name.endswith("_node") or name.startswith("kpi_") or name in {
            "router_node",
            "policy_qa_node",
            "hybrid_node",
            "scenario_node",
            "vendor_rating_node",
            "rag_fallback_node",
        }:
            return name
    return default


class TracedChatModel:
    """Thin proxy around ChatOpenAI that records latency + token usage."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        step_name = kwargs.pop("step_name", None) or _caller_step_name("llm")
        started = time.perf_counter()
        response = self._llm.invoke(*args, **kwargs)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        prompt_tokens, completion_tokens = extract_token_usage(response)
        record_step(
            tool_called=step_name,
            tool_latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            detail={"kind": "llm"},
        )
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._llm, name)


def wrap_llm(llm: Any) -> TracedChatModel:
    if isinstance(llm, TracedChatModel):
        return llm
    return TracedChatModel(llm)
