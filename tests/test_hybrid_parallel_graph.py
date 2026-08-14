"""Graph structure tests for parallel hybrid fan-out (no cloud credentials)."""

from __future__ import annotations


def test_graph_contains_parallel_hybrid_nodes():
    from graph.graph import build_graph

    graph = build_graph(use_checkpointer=False)
    node_names = set(graph.get_graph().nodes)
    for name in (
        "hybrid_dispatch",
        "hybrid_policy",
        "hybrid_kpi",
        "hybrid_aggregate",
        "policy_qa",
        "kpi",
        "router",
        "review",
    ):
        assert name in node_names


def test_hybrid_fanout_edges_exist():
    from graph.graph import build_graph

    graph = build_graph(use_checkpointer=False)
    g = graph.get_graph()
    edges = {(str(u), str(v)) for u, v, *_ in g.edges}
    assert ("hybrid_dispatch", "hybrid_policy") in edges
    assert ("hybrid_dispatch", "hybrid_kpi") in edges
    assert ("hybrid_policy", "hybrid_aggregate") in edges
    assert ("hybrid_kpi", "hybrid_aggregate") in edges
    assert ("hybrid_aggregate", "review") in edges
