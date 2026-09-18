"""Regression tests for defects found in the LegalGraphify v0.1.0 audit.

Each test below reproduces a concrete defect that was observed on the v0.1.0
tree and must hold after the fix. They are intentionally narrow: no network,
no writes to the bundled seed graph.
"""
import json
import os
import subprocess
import sys
import warnings

import pytest

from legal_graphify.agents.doc2md_agent import Doc2MarkdownAgent
from legal_graphify.core.engine import LegalGraphEngine
from legal_graphify.extractors.doc2md import extract_text_from_source


# ---------------------------------------------------------------------------
# D1 — A corrupt graph file used to be swallowed by `except Exception: pass`
#      (bandit B110/B112), leaving an empty engine that answered every query
#      with a misleading "not found" instead of surfacing the real problem.
# ---------------------------------------------------------------------------
def test_corrupt_graph_file_raises_instead_of_silently_emptying_the_engine(tmp_path):
    corrupt = tmp_path / "corrupt_graph.json"
    corrupt.write_text('{ "nodes": [ this is not valid json', encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        LegalGraphEngine(graph_path=str(corrupt))
    assert "corrupt_graph.json" in str(excinfo.value)


def test_json_without_node_link_structure_raises(tmp_path):
    not_a_graph = tmp_path / "not_a_graph.json"
    not_a_graph.write_text(json.dumps({"hello": "world"}), encoding="utf-8")

    with pytest.raises(ValueError):
        LegalGraphEngine(graph_path=str(not_a_graph))


def test_missing_graph_file_still_yields_an_empty_engine(tmp_path):
    """A missing path is a legitimate state (no seed bundled) and must NOT raise."""
    engine = LegalGraphEngine(graph_path=str(tmp_path / "does_not_exist.json"))
    assert engine.is_built is False
    assert engine.graph.number_of_nodes() == 0


def test_valid_but_empty_node_link_graph_does_not_raise(tmp_path):
    """A serialized empty graph round-trips instead of exploding."""
    empty = tmp_path / "empty.json"
    empty.write_text(
        json.dumps({"directed": True, "multigraph": False, "graph": {}, "nodes": [], "links": []}),
        encoding="utf-8",
    )
    engine = LegalGraphEngine(graph_path=str(empty))
    assert engine.graph.number_of_nodes() == 0


# ---------------------------------------------------------------------------
# D2 — `obras_index` was only created inside `_rebuild_indices`, so it did not
#      exist on an engine whose graph file was absent (find_node even had to
#      defend itself with getattr(...)).
# ---------------------------------------------------------------------------
def test_obras_index_is_initialized_by_the_constructor(tmp_path):
    engine = LegalGraphEngine(graph_path=str(tmp_path / "does_not_exist.json"))
    assert engine.obras_index == {}


# ---------------------------------------------------------------------------
# D3 — `extract_text_from_source("missing.pdf")` returned the literal filename
#      as if it were doctrine, so `legal-graphify ingest typo.pdf` reported
#      success with zero institutions instead of failing loudly.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("missing", ["tratado_inexistente.pdf", "acta.docx", "notas.txt", "doc.md"])
def test_extractor_rejects_path_shaped_source_that_does_not_exist(missing, tmp_path):
    candidate = tmp_path / missing
    with pytest.raises(FileNotFoundError):
        extract_text_from_source(str(candidate))


def test_raw_text_without_document_extension_is_still_treated_as_text():
    text = "La simulacion es un vicio del acto juridico segun el Art. 1707 CC."
    assert extract_text_from_source(text) == text


def test_agent_reports_missing_document_as_a_failed_run_not_a_success():
    res = Doc2MarkdownAgent().run(source="tratado_imprevision.pdf")
    assert res["success"] is False
    assert "tratado_imprevision.pdf" in res["error"]


def test_cli_ingest_of_missing_document_exits_non_zero(tmp_path, capsys):
    from legal_graphify import cli

    argv_backup = sys.argv
    sys.argv = ["legal-graphify", "ingest", str(tmp_path / "nope.pdf")]
    try:
        with pytest.raises(SystemExit) as excinfo:
            cli.main()
    finally:
        sys.argv = argv_backup

    assert excinfo.value.code == 1
    assert "nope.pdf" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# D4 — `nx.node_link_graph(data)` was called without the `edges` kwarg, which
#      emits a FutureWarning on networkx < 3.6 and silently changes the default
#      to "edges" on >= 3.6 (CI matrix spans both).
# ---------------------------------------------------------------------------
def test_loading_does_not_rely_on_the_ambiguous_node_link_default(tmp_path):
    graph_file = tmp_path / "legacy_links_only.json"
    graph_file.write_text(
        json.dumps(
            {
                "directed": True,
                "multigraph": False,
                "graph": {},
                "nodes": [
                    {"id": "inst_a", "label": "A", "node_type": "institucion"},
                    {"id": "norma_b", "label": "B", "node_type": "articulo_legal"},
                ],
                "links": [{"source": "inst_a", "target": "norma_b", "relation": "fundamenta_en"}],
            }
        ),
        encoding="utf-8",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        engine = LegalGraphEngine(graph_path=str(graph_file))

    assert engine.graph.number_of_nodes() == 2
    assert engine.graph.has_edge("inst_a", "norma_b")
    node_link_warnings = [
        w for w in caught if issubclass(w.category, FutureWarning) and "node_link" in str(w.message)
    ]
    assert node_link_warnings == [], f"ambiguous node_link_graph default: {node_link_warnings}"


# ---------------------------------------------------------------------------
# D5 — `python -m legal_graphify` failed: the package had no `__main__` module,
#      so only the console script was usable.
# ---------------------------------------------------------------------------
def test_package_is_executable_with_python_m():
    proc = subprocess.run(
        [sys.executable, "-m", "legal_graphify", "stats"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    assert proc.returncode == 0, proc.stderr
    assert "Total Nodes" in proc.stdout
