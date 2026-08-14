"""Safe graph invoke helpers that always supply a checkpoint thread_id."""

from __future__ import annotations

import uuid
from typing import Any


def thread_config(thread_id: str | None = None) -> dict[str, Any]:
    tid = thread_id or str(uuid.uuid4())
    return {"configurable": {"thread_id": tid}}, tid


def invoke_graph(graph: Any, state: dict[str, Any], *, thread_id: str | None = None) -> dict[str, Any]:
    config, tid = thread_config(thread_id)
    payload = dict(state)
    payload.setdefault("thread_id", tid)
    payload.setdefault("review_attempts", 0)
    return graph.invoke(payload, config)
