"""Unit tests for LegalGraphify Engine."""
import pytest
from legal_graphify.core.engine import LegalGraphEngine


@pytest.fixture(scope="module")
def engine():
    eng = LegalGraphEngine()
    assert eng.graph.number_of_nodes() > 0
    return eng


def test_graph_loaded(engine):
    assert engine.graph.number_of_nodes() >= 500
    assert engine.graph.number_of_edges() >= 500


def test_query_subgraph(engine):
    res = engine.query_subgraph("simulacion", max_hops=1)
    assert res["found"] is True
    assert "institucion:" in res["subgraph_yaml"]
    assert res["token_metrics"]["savings_pct"] >= 70.0


def test_pathfinding(engine):
    res = engine.path("simulacion", "nulidad", max_paths=2)
    assert res["found"] is True
    assert len(res["paths"]) > 0
    assert res["paths"][0]["hops"] >= 1


def test_explain(engine):
    res = engine.explain("simulacion")
    assert res["found"] is True
    assert "La Simulación" in res["label"]
    assert len(res["statutes"]) > 0


def test_blast_radius(engine):
    res = engine.affected("Art. 2515 CC")
    assert res["found"] is True
    assert res["metrics"]["total_entities_affected"] > 0


def test_god_nodes(engine):
    res = engine.god_nodes(top_n=5)
    assert len(res["god_institutions"]) == 5
    assert len(res["god_statutes"]) == 5
    assert res["god_institutions"][0]["pagerank"] > 0


def test_mermaid_generation(engine):
    diagram = engine.mermaid("simulacion", hops=1)
    assert "```mermaid" in diagram
    assert "classDef central" in diagram
