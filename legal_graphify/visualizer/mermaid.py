"""Mermaid diagram generator for Legal Subgraphs."""
from typing import Set
import networkx as nx


def generate_mermaid(graph: nx.DiGraph, center_node: str, max_hops: int = 1) -> str:
    """Renders a styled Mermaid graph centered around a focal legal node."""
    if not graph.has_node(center_node):
        return "```mermaid\ngraph TD\n    A[\"Node not found\"]\n```"

    sub_nodes: Set[str] = {center_node}
    current_layer = {center_node}
    for _ in range(max_hops):
        next_layer = set()
        for n in current_layer:
            next_layer.update(graph.successors(n))
            next_layer.update(graph.predecessors(n))
        sub_nodes.update(next_layer)
        current_layer = next_layer

    lines = [
        "```mermaid",
        "---",
        f"title: Subgrafo LegalGraphify — {graph.nodes[center_node].get('label', center_node)}",
        "---",
        "graph TD",
        "    classDef central fill:#1a237e,stroke:#3949ab,stroke-width:3px,color:#ffffff,font-weight:bold;",
        "    classDef institucion fill:#e8eaf6,stroke:#3f51b5,stroke-width:2px,color:#1a237e;",
        "    classDef norma fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;",
        "    classDef fallo fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#bf360c;",
        "    classDef via fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#880e4f;",
        "    classDef autor fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c;",
        ""
    ]

    for nid in sorted(sub_nodes):
        data = graph.nodes[nid]
        lbl = data.get("label", nid).replace('"', "'").replace("\n", " ")
        if len(lbl) > 40:
            lbl = lbl[:37] + "..."
        ntype = data.get("node_type", "institucion")
        lines.append(f'    {nid}["{lbl}"]')
        
        if nid == center_node:
            lines.append(f"    class {nid} central;")
        elif ntype in ("institucion", "obra"):
            lines.append(f"    class {nid} institucion;")
        elif ntype == "articulo_legal":
            lines.append(f"    class {nid} norma;")
        elif ntype == "jurisprudencia":
            lines.append(f"    class {nid} fallo;")
        elif ntype == "via_procesal":
            lines.append(f"    class {nid} via;")
        elif ntype == "autor":
            lines.append(f"    class {nid} autor;")

    lines.append("")
    subgraph = graph.subgraph(sub_nodes)
    for u, v, data in subgraph.edges(data=True):
        rel = data.get("relation", "")
        if rel:
            lines.append(f"    {u} -->|{rel.replace('_', ' ')}| {v}")
        else:
            lines.append(f"    {u} --> {v}")

    lines.append("```")
    return "\n".join(lines)
