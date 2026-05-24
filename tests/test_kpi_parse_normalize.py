from core.kpi_parse_utils import normalize_kpi_parse


def test_multi_metric_clears_clarification():
    q = "Show the on-time delivery rate and defect rate of yarn suppliers in 2025."
    parsed = {
        "need_clarification": True,
        "clarification_reason": "User requests two metrics",
        "metric": "on_time_delivery_rate_pct",
    }
    out = normalize_kpi_parse(q, parsed)
    assert out["need_clarification"] is False
    assert out.get("clarification_reason") is None
    assert "on_time_delivery_rate_pct" in out.get("metrics", [])


def test_template_match_clears_clarification():
    q = "Show yarn supplier on-time delivery in 2025"
    parsed = {"need_clarification": True, "clarification_reason": "ambiguous"}
    out = normalize_kpi_parse(q, parsed)
    assert out["need_clarification"] is False
