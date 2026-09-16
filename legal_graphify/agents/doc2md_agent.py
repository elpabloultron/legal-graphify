"""
LegalGraphify — Agente Ingestor Doctrinal y Conversor a Markdown Canónico (Doc2MarkdownAgent)
Transforma textos jurídicos desestructurados, PDFs y documentos en Markdown canónico token-optimizado
y los asimila de forma incremental en el Knowledge Graph de LegalGraphify.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from legal_graphify.extractors.doc2md import (
    extract_text_from_source,
    convert_text_to_canonical_markdown,
)
from legal_graphify.core.engine import LegalGraphEngine


class Doc2MarkdownAgent:
    """
    Agente autónomo de ingesta y normalización documental para LegalGraphify.
    Convierte fuentes desestructuradas a Markdown canónico (estándar RAE/ASALE y estilo procesal chileno)
    y sincroniza los nuevos nodos y aristas con el grafo de conocimiento.
    """

    def __init__(self, engine: Optional[LegalGraphEngine] = None):
        self.engine = engine or LegalGraphEngine()

    def run(
        self,
        source: str | Path,
        output_path: Optional[str] = None,
        author: Optional[str] = None,
        area: Optional[str] = None,
        work: Optional[str] = None,
        subject: Optional[str] = None,
        update_graph: bool = False,
        save_graph: bool = True,
    ) -> Dict[str, Any]:
        """
        Ejecuta el pipeline de ingesta, conversión y actualización del grafo.
        """
        source_desc = str(source) if isinstance(source, (str, Path)) and os.path.exists(str(source)) else "Texto directo"

        # 1. Extracción de texto crudo
        raw_text = extract_text_from_source(source)
        if not raw_text or len(raw_text.strip()) < 10:
            return {
                "success": False,
                "error": "El contenido extraído está vacío o no contiene texto suficiente.",
                "source": source_desc,
            }

        # 2. Configurar metadatos
        meta: Dict[str, str] = {}
        if author:
            meta["autor"] = author.strip()
        if area:
            meta["area"] = area.strip()
        if work:
            meta["obra"] = work.strip()
        if subject:
            meta["materia"] = subject.strip()

        # 3. Transformación a Markdown Canónico
        canonical_md = convert_text_to_canonical_markdown(raw_text, metadata=meta)

        # 4. Guardar archivo en disco si se solicitó
        saved_file = None
        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                f.write(canonical_md)
            saved_file = str(out_p.resolve())

        # 5. Asimilación en el grafo si se solicitó
        graph_stats = None
        if update_graph:
            graph_stats = self.engine.ingest_markdown_content(canonical_md, auto_save=save_graph)

        return {
            "success": True,
            "source": source_desc,
            "output_file": saved_file,
            "metadata": meta,
            "raw_characters": len(raw_text),
            "canonical_characters": len(canonical_md),
            "canonical_markdown": canonical_md,
            "graph_updated": update_graph,
            "graph_stats": graph_stats,
        }
