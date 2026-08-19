"""Unified *observability* for recovery — not a one-size-fits-all fallback decorator.

Three failure types in this project are not the same mechanism:

- ``fallback``: capability drop (Cross-Encoder → embedding → noop reranker)
- ``retry_repair``: error recovery (NL2SQL execute → repair once → re-execute)
- ``partial_degradation``: keep serving with reduced recall (Pinecone down → BM25-only)

Call ``record_resilience_event`` whenever one of these fires so Monitor can count
them. Do not wrap SQL repair and reranker fallback in a single ``@with_fallback``.
"""

from __future__ import annotations

from typing import Any, Literal

Strategy = Literal["fallback", "retry_repair", "partial_degradation"]

BM25_ONLY_LIMITATION_EN = (
    "Vector search (Pinecone) was unavailable; this answer used keyword (BM25) "
    "retrieval only. Semantic matches may be missing."
)
BM25_ONLY_LIMITATION_ZH = (
    "向量检索不可用，本次仅使用关键词（BM25）检索，语义召回可能不完整。"
)


def record_resilience_event(
    strategy: Strategy,
    *,
    from_backend: str,
    to_backend: str,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> None:
    """Append a resilience step to the active trace (no-op if no trace is open)."""
    detail: dict[str, Any] = {
        "kind": "resilience",
        "strategy": strategy,
        "from": from_backend,
        "to": to_backend,
        "reason": (reason or "")[:500],
    }
    if extra:
        detail.update(extra)
    try:
        from observability.recorder import record_step

        record_step("resilience", detail=detail)
    except Exception:  # noqa: BLE001 — never fail the user request for telemetry
        return
