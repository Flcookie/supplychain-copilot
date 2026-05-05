# Baseline Audit (Pre-Optimization)

This file captures the baseline behavior before the resume-alignment upgrade.

## Workflow Baseline
- LangGraph path: `router -> policy_qa|kpi|scenario -> answer`.
- Router output originally only returned `intent`.
- No built-in `confidence`, `reason`, or `ambiguity_type` fields.

## Explainability Baseline
- Policy path exposed retrieved documents in UI.
- KPI and Scenario paths did not provide a normalized evidence contract.
- SQL execution metadata (latency/row_count) was not recorded in state.

## Reliability/Safety Baseline
- Low-confidence routing fallback was not implemented.
- Ambiguity clarification loop was not implemented.
- Scenario SQL used string interpolation for `country` filter.
- SQL execution had no programmatic read-only validator.

## Evaluation Baseline
- No versioned A/B router benchmark script.
- No test dataset covering policy, KPI, scenario and ambiguity edge cases.

## Current Upgrade Target
- Introduce router structured output and decoupled decision logic:
  1) ambiguity check first
  2) confidence threshold second
  3) then intent route
