"""Aggregate Copilot traces into interview-ready online metrics.

This is observability + badcase-driven iteration, not automatic adaptive routing.
Numbers come from ``data/traces.db``; they are empty until the Copilot has been used.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from observability.store import TraceStore, get_store

DEFAULT_WINDOW_HOURS = 24 * 7
LOW_CONFIDENCE_THRESHOLD = 0.75


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return round(xs[0], 2)
    k = (len(xs) - 1) * p
    floor = int(k)
    ceil = min(floor + 1, len(xs) - 1)
    if floor == ceil:
        return round(xs[floor], 2)
    return round(xs[floor] + (xs[ceil] - xs[floor]) * (k - floor), 2)


def _truthy_int(value: Any) -> bool:
    if value is True or value == 1:
        return True
    if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes"}:
        return True
    return False


def traces_in_window(
    store: TraceStore | None = None,
    *,
    hours: float | None = DEFAULT_WINDOW_HOURS,
    limit: int = 10_000,
) -> list[dict[str, Any]]:
    active = store or get_store()
    traces = active.list_traces(limit=limit)
    if hours is None:
        return traces
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out: list[dict[str, Any]] = []
    for row in traces:
        parsed = _parse_ts(row.get("timestamp"))
        if parsed is None or parsed >= cutoff:
            out.append(row)
    return out


def summarize_metrics(
    store: TraceStore | None = None,
    *,
    hours: float | None = DEFAULT_WINDOW_HOURS,
    low_confidence: float = LOW_CONFIDENCE_THRESHOLD,
) -> dict[str, Any]:
    """Return router / HITL / review / latency / token aggregates for a time window."""
    rows = traces_in_window(store, hours=hours)
    n = len(rows)
    intent_counts: Counter[str] = Counter()
    confidence_by_intent: dict[str, list[float]] = defaultdict(list)
    latencies: list[float] = []
    prompt_tokens = 0
    completion_tokens = 0
    clarified = 0
    hitl = 0
    review_boost = 0
    low_conf = 0
    errors = 0
    confidences: list[float] = []

    for row in rows:
        intent = row.get("intent") or "unknown"
        intent_counts[intent] += 1
        conf = row.get("confidence")
        if isinstance(conf, (int, float)):
            confidences.append(float(conf))
            confidence_by_intent[intent].append(float(conf))
            if float(conf) < low_confidence:
                low_conf += 1
        lat = row.get("total_latency_ms")
        if isinstance(lat, (int, float)):
            latencies.append(float(lat))
        prompt_tokens += int(row.get("total_prompt_tokens") or 0)
        completion_tokens += int(row.get("total_completion_tokens") or 0)
        if row.get("ambiguity_type"):
            clarified += 1
        if _truthy_int(row.get("human_approval_required")):
            hitl += 1
        if row.get("review_status") == "needs_more_evidence":
            review_boost += 1
        if row.get("error"):
            errors += 1

    intent_distribution = []
    for intent, count in intent_counts.most_common():
        vals = confidence_by_intent.get(intent) or []
        intent_distribution.append(
            {
                "intent": intent,
                "count": count,
                "share": round(count / n, 4) if n else 0.0,
                "mean_confidence": round(sum(vals) / len(vals), 4) if vals else None,
            }
        )

    return {
        "window_hours": hours,
        "traces": n,
        "errors": errors,
        "error_rate": round(errors / n, 4) if n else 0.0,
        "router_intent_distribution": intent_distribution,
        "mean_confidence": round(sum(confidences) / len(confidences), 4) if confidences else None,
        "low_confidence_rate": round(low_conf / n, 4) if n else 0.0,
        "clarification_rate": round(clarified / n, 4) if n else 0.0,
        "hitl_trigger_rate": round(hitl / n, 4) if n else 0.0,
        "review_evidence_boost_rate": round(review_boost / n, 4) if n else 0.0,
        "p50_latency_ms": _percentile(latencies, 0.50),
        "p95_latency_ms": _percentile(latencies, 0.95),
        "mean_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "total_prompt_tokens": prompt_tokens,
        "total_completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "low_confidence_threshold": low_confidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print aggregated Copilot trace metrics (human-in-the-loop iteration, not auto-tuning)."
    )
    parser.add_argument("--hours", type=float, default=DEFAULT_WINDOW_HOURS)
    parser.add_argument("--all-time", action="store_true", help="Ignore the time window.")
    args = parser.parse_args()
    hours = None if args.all_time else args.hours
    payload = summarize_metrics(hours=hours)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
