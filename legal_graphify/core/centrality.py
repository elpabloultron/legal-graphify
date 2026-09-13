"""Centrality, PageRank, and Community Detection algorithms for Legal Knowledge Graphs."""
from typing import Dict, Any, List, Tuple
import networkx as nx


def compute_pagerank(graph: nx.DiGraph, alpha: float = 0.85, max_iter: int = 100) -> Dict[str, float]:
    """Computes PageRank scores across all legal nodes."""
    try:
        return nx.pagerank(graph, alpha=alpha, max_iter=max_iter)
    except Exception:
        # Fallback to in-degree weighting
        return {n: float(graph.in_degree(n) + 1) for n in graph.nodes()}


def detect_communities(graph: nx.DiGraph) -> Dict[str, int]:
    """Applies Clauset-Newman-Moore greedy modularity community detection."""
    community_map: Dict[str, int] = {}
    try:
        undirected = graph.to_undirected()
        communities = nx.algorithms.community.greedy_modularity_communities(undirected)
        for idx, comm in enumerate(communities):
            for node_id in comm:
                community_map[node_id] = idx
    except Exception:
        for idx, node_id in enumerate(graph.nodes()):
            community_map[node_id] = 0
    return community_map


def extract_god_nodes(graph: nx.DiGraph, top_n: int = 10) -> Dict[str, Any]:
    """Identifies structural pillar nodes (God Nodes) using PageRank and degree centrality."""
    scores = compute_pagerank(graph)
    degrees = dict(graph.degree())
    
    sorted_nodes = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    
    instituciones: List[Dict[str, Any]] = []
    normas: List[Dict[str, Any]] = []
    
    for nid, score in sorted_nodes:
        data = graph.nodes.get(nid, {})
        ntype = data.get("node_type", "unknown")
        lbl = data.get("label", nid)
        deg = degrees.get(nid, 0)
        
        entry = {
            "id": nid,
            "label": lbl,
            "node_type": ntype,
            "pagerank": round(score, 5),
            "degree": deg,
            "community": data.get("community", 0)
        }
        
        if ntype in ("institucion", "obra") and len(instituciones) < top_n:
            instituciones.append(entry)
        elif ntype == "articulo_legal" and len(normas) < top_n:
            normas.append(entry)
            
        if len(instituciones) >= top_n and len(normas) >= top_n:
            break
            
    return {
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "god_institutions": instituciones,
        "god_statutes": normas
    }
