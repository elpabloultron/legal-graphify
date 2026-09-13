"""Statutory & BCN Code Extractor for Legal Knowledge Graphs."""
import re
from typing import Dict, Any, List
import networkx as nx
from legal_graphify.extractors.doctrine import sanitize_id


def extract_articles_from_statute(statute_code: str, text: str) -> nx.DiGraph:
    """Parses statutory code text (e.g. Código Civil, CPC) into an article graph."""
    graph = nx.DiGraph()
    statute_id = sanitize_id(statute_code, "codigo")
    graph.add_node(statute_id, label=statute_code, node_type="cuerpo_legal", community=2)

    # Simple regex for articles: Art. 123 or Artículo 123
    pattern = re.compile(r"(?:Art[íi]culo|Art\.)\s+(\d+[\w\s\.-]*?)(?=(?:Art[íi]culo|Art\.)\s+\d+|\Z)", re.IGNORECASE | re.DOTALL)
    
    for match in pattern.finditer(text):
        chunk = match.group(0).strip()
        header_match = re.match(r"(?:Art[íi]culo|Art\.)\s+(\d+(?:\s*(?:bis|ter|quater))?)", chunk, re.IGNORECASE)
        if header_match:
            art_num = header_match.group(1).strip()
            art_lbl = f"{statute_code}, Art. {art_num}"
            art_id = sanitize_id(art_lbl, "norma")
            
            body = chunk[header_match.end():].strip().lstrip(".-: ")
            graph.add_node(
                art_id,
                label=art_lbl,
                node_type="articulo_legal",
                texto=body[:500],
                community=2
            )
            graph.add_edge(art_id, statute_id, relation="pertenece_a")

    return graph
