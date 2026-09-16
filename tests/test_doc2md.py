"""Unit tests for LegalGraphify doc2md extraction and Doc2MarkdownAgent."""
import os
import sys
import tempfile
import pytest
from pathlib import Path

from legal_graphify.extractors.doc2md import (
    clean_unwanted_hyphens_and_breaks,
    apply_ortotipografia_rae_chile,
    standardize_legal_citations,
    convert_text_to_canonical_markdown,
    extract_text_from_source,
)
from legal_graphify.agents.doc2md_agent import Doc2MarkdownAgent
from legal_graphify.core.engine import LegalGraphEngine


SAMPLE_RAW_LEGAL_TEXT = """
Página 12 de 85
--- 12 ---

1. DE LA TEORÍA DE LA IMPREVISIÓN Y CASO FORTUITO

El caso fortuito o fuerza mayor se encuentra definido en el artículo 45 del Código Civil
como el imprevisto a que no es posible resistir. La jurisprudencia de la Corte Suprema, en
particular en el Rol 18.234-2021 de la Corte Suprema, ha reiterado que requiere una
irresistibilidad objetiva y una causa com-
pletamente exterior.

Por su parte, la imprevisión contractual no se encuentra expresamente consagrada en el Código Civil,
pero la doctrina moderna liderada por autores nacionales sostiene que en virtud del artículo 1545 del Código Civil
y el principio de buena fe (artículo 1546 del Código Civil), el juez puede revisar el contrato.

Requisitos copulativos:
a) Suceso imprevisible al momento de contratar.
b) Excesiva onerosidad sobreviniente que altere el equilibrio económico en más de un 50.5%.
c) Ausencia de culpa o mora del deudor.

Operativa procesal forense:
Se hace valer como excepción perentoria de inejecución inimputable o mediante demanda ordinaria de
resolución contractual o reajuste por excesiva onerosidad sobreviniente en juicio ordinario de mayor cuantía.
El plazo de prescripción se rige por las reglas generales de 5 años según el artículo 2515 del Código Civil.
El RUT de la parte demandada es 15345678-k y la ley aplicable es la Ley 21.643, Art. 2.
"""


def test_clean_unwanted_hyphens_and_breaks():
    cleaned = clean_unwanted_hyphens_and_breaks(SAMPLE_RAW_LEGAL_TEXT)
    # Verifica que com-\npletamente se unió a completamente
    assert "completamente" in cleaned
    assert "com-\npletamente" not in cleaned
    # Verifica que se suprimieron los encabezados de página
    assert "Página 12 de 85" not in cleaned
    assert "--- 12 ---" not in cleaned


def test_apply_ortotipografia_rae_chile():
    raw = 'El deudor alegó "caso fortuito." El tribunal desestimó con un 25.5% de probabilidad para el RUT 12345678-k según el Art 1545.'
    res = apply_ortotipografia_rae_chile(raw)

    # 1. Comillas latinas y punto exterior
    assert "«caso fortuito»." in res
    # 2. Coma decimal y espacio en porcentaje
    assert "25,5 %" in res
    # 3. RUT punteado con K mayúscula
    assert "12.345.678-K" in res
    # 4. Abreviatura Art.
    assert "Art. 1545" in res


def test_standardize_legal_citations():
    text = "Conforme al Art. 1545 del Código Civil y el Art. 161 del Código del Trabajo, además del Rol 12.345-2023 de la Corte Suprema y la Ley 21.643, Art. 2."
    std = standardize_legal_citations(text)

    assert "[BCN - Código Civil, Art. 1545]" in std
    assert "[BCN - Código del Trabajo, Art. 161]" in std
    assert "[CS - Rol N° 12.345-2023]" in std
    assert "[BCN - Ley N° 21643, Art. 2]" in std


def test_convert_text_to_canonical_markdown():
    metadata = {
        "obra": "Tratado de Derecho de las Obligaciones",
        "autor": "René Ramos Pazos",
        "area": "Derecho Civil",
        "materia": "Efectos de las Obligaciones y Responsabilidad Contractual"
    }
    md = convert_text_to_canonical_markdown(SAMPLE_RAW_LEGAL_TEXT, metadata=metadata)

    # Verificar encabezado y metadatos
    assert "# TRATADO DE DERECHO DE LAS OBLIGACIONES" in md
    assert "**Tratadista:** René Ramos Pazos" in md
    assert "**Área:** Derecho Civil" in md
    assert "> 💡 *Base Doctrinal Canónica (Token-Optimized) para LegalGraphify y Open Legal Chile.*" in md

    # Verificar estructura canónica de instituciones
    assert "## 🏛️" in md
    assert "**Definición Canónica:**" in md
    assert "**Operativa Procesal Forense:**" in md
    assert "**Concordancias Legales:**" in md
    assert "**Criterio Jurisprudencial Rector:**" in md

    # Verificar corchetes y ortotipografía dentro del markdown generado
    assert "[BCN - Código Civil" in md
    assert "[CS - Rol N°" in md


def test_extract_text_from_source_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write(SAMPLE_RAW_LEGAL_TEXT)
        tmp_path = tmp.name

    try:
        extracted = extract_text_from_source(tmp_path)
        assert "DE LA TEORÍA DE LA IMPREVISIÓN" in extracted
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_doc2md_agent_file_output():
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_file = os.path.join(tmp_dir, "imprevision.md")
        agent = Doc2MarkdownAgent()
        res = agent.run(
            source=SAMPLE_RAW_LEGAL_TEXT,
            output_path=output_file,
            author="Jorge López Santa María",
            area="Derecho Civil",
            work="Los Contratos: Parte General",
            update_graph=False,
        )

        assert res["success"] is True
        assert os.path.exists(output_file)
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "## 🏛️" in content
        assert "Jorge López Santa María" in content


def test_engine_incremental_ingest():
    engine = LegalGraphEngine()
    initial_nodes = engine.graph.number_of_nodes()

    metadata = {
        "obra": "Doctrina de Prueba Incremental",
        "autor": "Jurista de Prueba",
        "area": "Derecho Civil",
        "materia": "Materia Nueva de Prueba"
    }
    canonical_md = convert_text_to_canonical_markdown(SAMPLE_RAW_LEGAL_TEXT, metadata=metadata)

    # Ingestar sin guardar en disco para no alterar el json maestro durante los tests
    res = engine.ingest_markdown_content(canonical_md, auto_save=False)

    assert res["success"] is True
    assert res["institutions_added"] >= 1
    assert res["nodes_added"] > 0
    assert engine.graph.number_of_nodes() > initial_nodes

    # Verificar que el nuevo nodo fue indexado y se puede consultar
    found_inst = any("imprevisión" in k.lower() or "caso fortuito" in k.lower() for k in engine.instituciones_index.keys())
    assert found_inst is True


def test_cli_ingest_command(capsys):
    from legal_graphify.cli import main

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write(SAMPLE_RAW_LEGAL_TEXT)
        tmp_path = tmp.name

    try:
        sys_argv_backup = sys.argv
        sys.argv = ["legal-graphify", "ingest", tmp_path, "--author", "Test Autor", "--no-save"]
        main()
        captured = capsys.readouterr()
        assert "CANONICAL MARKDOWN" in captured.out
        assert "Test Autor" in captured.out
    finally:
        sys.argv = sys_argv_backup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_mcp_tool_ingest():
    import asyncio
    from legal_graphify.mcp.server import HAS_FASTMCP
    if not HAS_FASTMCP:
        pytest.skip("fastmcp no está instalado en el entorno actual")
    from legal_graphify.mcp.server import create_mcp_app
    mcp = create_mcp_app()
    tool = asyncio.run(mcp.get_tool("ingest_document_to_markdown"))
    assert tool is not None
    assert tool.name == "ingest_document_to_markdown"


