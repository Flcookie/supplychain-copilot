"""Lightweight observability panel for Copilot traces.

Run:
    streamlit run app/observability_ui.py
"""

from __future__ import annotations

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import streamlit as st

from observability.metrics import summarize_metrics
from observability.store import get_store

st.set_page_config(page_title="Copilot Observability", page_icon="📡", layout="wide")

st.title("Copilot Observability")
st.caption(
    "Local observability — trace steps, latency, tokens, router / HITL rates. "
    "This is a human-in-the-loop iteration loop (metrics → badcase → config), not auto-tuning."
)

store = get_store()

with st.sidebar:
    st.header("Controls")
    n_steps = st.slider("Recent steps (N)", min_value=20, max_value=500, value=100, step=20)
    n_traces = st.slider("Recent traces", min_value=10, max_value=200, value=50, step=10)
    if st.button("Refresh"):
        st.rerun()
    if st.button("Clear all traces", type="secondary"):
        store.delete_all()
        st.success("Cleared.")
        st.rerun()
    st.markdown("---")
    st.markdown(f"`{store.db_path}`")

traces = store.list_traces(limit=n_traces)
steps = store.list_recent_steps(limit=n_steps)

# --- KPI strip ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Traces", len(traces))
c2.metric("Steps shown", len(steps))
if traces:
    avg_lat = pd.Series(
        [t["total_latency_ms"] for t in traces if t.get("total_latency_ms") is not None]
    )
    avg_conf = pd.Series(
        [t["confidence"] for t in traces if t.get("confidence") is not None]
    )
    c3.metric("Avg E2E latency (ms)", f"{avg_lat.mean():.0f}" if not avg_lat.empty else "—")
    c4.metric("Avg confidence", f"{avg_conf.mean():.2f}" if not avg_conf.empty else "—")
else:
    c3.metric("Avg E2E latency (ms)", "—")
    c4.metric("Avg confidence", "—")

metrics = summarize_metrics(store, hours=None)
m5, m6, m7, m8 = st.columns(4)
m5.metric("Clarification rate", f"{metrics['clarification_rate']:.0%}")
m6.metric("HITL trigger rate", f"{metrics['hitl_trigger_rate']:.0%}")
m7.metric("Review boost rate", f"{metrics['review_evidence_boost_rate']:.0%}")
m8.metric(
    "P50 / P95 latency (ms)",
    (
        f"{metrics['p50_latency_ms']:.0f} / {metrics['p95_latency_ms']:.0f}"
        if metrics.get("p50_latency_ms") is not None and metrics.get("p95_latency_ms") is not None
        else "—"
    ),
)

st.markdown("---")

# --- Recent steps table ---
st.subheader("Recent call steps")
if not steps:
    st.info("No traces yet. Ask a question in the main Copilot UI (`streamlit run app/ui.py`) or replay below.")
else:
    df_steps = pd.DataFrame(steps)
    display_cols = [
        "step_timestamp",
        "query",
        "step_num",
        "tool_called",
        "tool_latency_ms",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "confidence",
        "intent",
    ]
    present = [c for c in display_cols if c in df_steps.columns]
    st.dataframe(df_steps[present], use_container_width=True, hide_index=True)

# --- Charts ---
st.subheader("Trends")
chart_col1, chart_col2 = st.columns(2)

if traces:
    df_traces = pd.DataFrame(traces).sort_values("timestamp")
    with chart_col1:
        st.markdown("**End-to-end latency (ms)**")
        if df_traces["total_latency_ms"].notna().any():
            lat_chart = df_traces.set_index("timestamp")[["total_latency_ms"]].rename(
                columns={"total_latency_ms": "latency_ms"}
            )
            st.line_chart(lat_chart)
        else:
            st.caption("No latency data yet.")
    with chart_col2:
        st.markdown("**Token usage per trace**")
        token_cols = [c for c in ("total_prompt_tokens", "total_completion_tokens") if c in df_traces.columns]
        if token_cols and df_traces[token_cols].sum().sum() > 0:
            tok_chart = df_traces.set_index("timestamp")[token_cols]
            st.line_chart(tok_chart)
        else:
            st.caption("No token usage recorded yet (check LLM response usage fields).")

    if steps:
        st.markdown("**Per-step latency by tool**")
        df_s = pd.DataFrame(steps).dropna(subset=["tool_latency_ms"]).sort_values("step_timestamp")
        if not df_s.empty:
            wide = (
                df_s.pivot_table(
                    index="step_timestamp",
                    columns="tool_called",
                    values="tool_latency_ms",
                    aggfunc="mean",
                )
                .sort_index()
            )
            st.line_chart(wide)
else:
    st.caption("Charts appear after the first traced run.")

st.markdown("---")

# --- Trace detail + replay ---
st.subheader("Trace detail & replay")
if not traces:
    st.caption("Nothing to replay yet.")
else:
    options = {
        f"{t['timestamp'][:19]} | {t.get('intent') or '?'} | conf={t.get('confidence')} | {(t['query'] or '')[:60]}": t[
            "id"
        ]
        for t in traces
    }
    label = st.selectbox("Select a historical trace", list(options.keys()))
    selected_id = options[label]
    selected = store.get_trace(selected_id)
    selected_steps = store.list_steps(selected_id)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Confidence", selected.get("confidence") if selected else "—")
    m2.metric("Intent", selected.get("intent") if selected else "—")
    m3.metric("E2E ms", selected.get("total_latency_ms") if selected else "—")
    m4.metric(
        "Tokens",
        (
            (selected.get("total_prompt_tokens") or 0)
            + (selected.get("total_completion_tokens") or 0)
        )
        if selected
        else "—",
    )

    if selected_steps:
        st.dataframe(pd.DataFrame(selected_steps), use_container_width=True, hide_index=True)

    with st.expander("Final answer", expanded=False):
        st.write(selected.get("final_answer") if selected else "")

    lang = (selected or {}).get("response_language") or "en"
    query = (selected or {}).get("query") or ""

    if st.button("Replay selected query", type="primary", disabled=not bool(query)):
        with st.spinner("Re-running Copilot…"):
            from api.services.copilot import run_copilot

            result = run_copilot(query, lang)
        st.success(
            f"Replay done · intent={result.get('intent')} · "
            f"confidence={result.get('route_info', {}).get('confidence')} · "
            f"trace_id={result.get('trace_id')}"
        )
        with st.expander("Replay answer", expanded=True):
            st.write(result.get("answer"))
        st.rerun()
