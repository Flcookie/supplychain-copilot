"""Heuristic router must not treat substrings like 'if' in 'certificates' as risk."""

from eval.run_router_eval import optimized_router, override_router


def test_certificates_does_not_match_if_substring():
    question = "Which vendor certificates lapse within two months?"
    heuristic = optimized_router(question)
    override = override_router(question)
    assert heuristic.intent != "risk_scenario"
    assert override.intent != "risk_scenario"


def test_standalone_if_still_routes_whatif_to_risk():
    question = "If Vietnam suppliers are delayed by 7 days, what is the impact?"
    assert optimized_router(question).intent == "risk_scenario"
    assert override_router(question).intent == "risk_scenario"


def test_heldout007_overbroad_gate_on_export_entire_dataset():
    question = "Please export every supplier's entire dataset."
    out = override_router(question)
    assert out.intent == "policy_qa"
    assert out.ambiguity_type == "overbroad_data_request"


def test_heldout009_them_triggers_coreference():
    question = "Compare them on delivery performance."
    out = override_router(question)
    assert out.intent == "kpi_query"
    assert out.ambiguity_type == "coreference"
