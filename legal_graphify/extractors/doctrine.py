"""Doctrinal Markdown extractor for Legal Knowledge Graphs."""
from __future__ import annotations

import os
import re
import unicodedata
from typing import Dict, Any, Tuple, Set, List, Optional
import networkx as nx


def normalize_str(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()


def sanitize_id(text: str, prefix: str = "") -> str:
    norm = normalize_str(text)
    clean = re.sub(r"[^a-z0-9]+", "_", norm).strip("_")
    if not clean:
        clean = "nodo"
    if clean[0].isdigit():
        clean = f"id_{clean}"
    if prefix:
        return f"{prefix}_{clean}"
    return clean


def parse_doctrine_markdown(
    content: str,
    graph: Optional[nx.DiGraph] = None,
    default_obra: str = "Doctrina Nacional"
) -> Tuple[nx.DiGraph, List[Dict[str, Any]]]:
    """
    Parsea el contenido de un texto Markdown canónico y lo asimila en el Knowledge Graph (nx.DiGraph).
    Retorna una tupla con el grafo actualizado y la lista de instituciones agregadas con sus métricas.
    """
    if graph is None:
        graph = nx.DiGraph()

    added_institutions: List[Dict[str, Any]] = []

    obra_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    obra = obra_match.group(1).strip() if obra_match else default_obra

    meta_match = re.search(
        r"\*\*Tratadistas?:\*\*\s*([^|]+)\|\s*\*\*Área:\*\*\s*([^|]+)\|\s*\*\*Materia:\*\*\s*(.+)$",
        content,
        re.MULTILINE
    )
    if meta_match:
        autor = meta_match.group(1).strip()
        area = meta_match.group(2).strip()
        materia = meta_match.group(3).strip()
    else:
        autor = "Doctrina Nacional"
        area = "Derecho Civil"
        materia = obra

    autor_id = sanitize_id(autor, "autor")
    if not graph.has_node(autor_id):
        graph.add_node(autor_id, label=autor, node_type="autor", community=1)

    obra_id = sanitize_id(obra, "obra")
    if not graph.has_node(obra_id):
        graph.add_node(obra_id, label=obra, node_type="obra", area=area, community=1)
    graph.add_edge(obra_id, autor_id, relation="escrito_por")

    secciones = re.split(r"\n##\s+(?:🏛️\s*)?", content)
    for sec in secciones:
        sec_clean = sec.strip()
        if not sec_clean or sec_clean.startswith("# ") or sec_clean.startswith("**Tratadista"):
            continue

        lines = sec_clean.split("\n")
        titulo = lines[0].strip().lstrip("#").strip()
        if not titulo or len(titulo) < 3:
            continue

        inst_id = sanitize_id(titulo, "inst")
        def_match = re.search(r"\*\*Definición Canónica(?:\s*\([^)]+\))?:\*\*\s*\n*(.*?)(?=\n\n|\n\*\*|\n\*|\Z)", sec_clean, re.DOTALL)
        definicion = def_match.group(1).strip() if def_match else (lines[1].strip()[:200] if len(lines) > 1 else "")

        proc_match = re.search(r"\*\*Operativa Procesal Forense:\*\*\s*\n*(.*?)(?=\n\n\*\*|\n\*\*Concordancias|\n\*\*Criterio|\n---\Z|\Z)", sec_clean, re.DOTALL)
        operativa_procesal = proc_match.group(1).strip() if proc_match else ""

        graph.add_node(
            inst_id,
            label=titulo,
            node_type="institucion",
            area=area,
            materia=materia,
            autor=autor,
            obra=obra,
            definicion=definicion,
            operativa_procesal=operativa_procesal,
            tokens_seccion=int(len(sec_clean.split()) * 1.3),
            tokens_completos=int(len(content.split()) * 1.3),
            community=0
        )
        graph.add_edge(inst_id, autor_id, relation="analizado_por")
        graph.add_edge(inst_id, obra_id, relation="contenido_en")

        # Concordancias normativas (soporta corchetes oficiales BCN y citas directas)
        concordancias_oficiales = re.findall(r"\[(BCN\s*-\s*[^\]]+)\]", sec_clean)
        concordancias_tradicionales = re.findall(
            r"(?:Arts?\.?\s*\d+(?:\s*(?:bis|ter|quater))?(?:\s*(?:inc\.?\s*\d+|N\.?°?\s*\d+))*\s*(?:del\s*)?(?:Código Civil|Código del Trabajo|CC|CPC|CPP|CP|COT|CT|CPR|Ley\s*\d+[\.\d]*))",
            sec_clean
        )
        todas_normas = set(concordancias_oficiales + concordancias_tradicionales)
        for norm_text in todas_normas:
            norm_id = sanitize_id(norm_text, "norma")
            if not graph.has_node(norm_id):
                graph.add_node(norm_id, label=norm_text, node_type="articulo_legal", community=2)
            graph.add_edge(inst_id, norm_id, relation="fundamenta_en")

        # Fallos y Jurisprudencia (soporta corchetes oficiales CS y citas Rol)
        fallos_oficiales = re.findall(r"\[((?:CS|C\.?A\.?)\s*-\s*Rol\s*[^\]]+)\]", sec_clean)
        fallos_tradicionales = re.findall(r"Rol\s*N\.?°?\s*\d+[\.\d]*-\d{4}", sec_clean)
        todos_fallos = set(fallos_oficiales + fallos_tradicionales)
        for f_text in todos_fallos:
            fallo_id = sanitize_id(f_text, "fallo")
            if not graph.has_node(fallo_id):
                graph.add_node(fallo_id, label=f_text, node_type="jurisprudencia", community=3)
            graph.add_edge(inst_id, fallo_id, relation="criterio_jurisprudencial")

        added_institutions.append({
            "id": inst_id,
            "titulo": titulo,
            "area": area,
            "autor": autor,
            "concordancias_count": len(todas_normas),
            "fallos_count": len(todos_fallos)
        })

    return graph, added_institutions


def extract_doctrine_directory(doctrine_dir: str) -> nx.DiGraph:
    """Parses legal doctrine markdown files into a directed Knowledge Graph."""
    graph = nx.DiGraph()

    for root, _, files in os.walk(doctrine_dir):
        if "doctrina_raw" in root:
            continue
        for file in sorted(files):
            if not file.endswith(".md") or file.startswith(".") or file == "README.md":
                continue

            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            parse_doctrine_markdown(content, graph=graph, default_obra=file.replace(".md", ""))

    return graph
