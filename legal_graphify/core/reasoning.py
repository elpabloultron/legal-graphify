"""Multi-hop Relational Reasoning, Pathfinding, and Impact Analysis."""
from typing import Dict, Any, List, Optional, Set
import networkx as nx


def find_shortest_paths(graph: nx.DiGraph, source: str, target: str, max_paths: int = 3) -> Dict[str, Any]:
    """Finds all shortest relational paths between two legal entities."""
    if not graph.has_node(source) or not graph.has_node(target):
        return {
            "found": False,
            "error": "Source or target node does not exist in graph."
        }

    undirected = graph.to_undirected()
    if not nx.has_path(undirected, source, target):
        return {
            "found": False,
            "source": graph.nodes[source].get("label", source),
            "target": graph.nodes[target].get("label", target),
            "message": "No connecting path found between nodes."
        }

    paths = []
    try:
        gen = nx.all_shortest_paths(undirected, source=source, target=target)
        for i, p in enumerate(gen):
            if i >= max_paths:
                break
            paths.append(p)
    except Exception:
        try:
            paths.append(nx.shortest_path(undirected, source=source, target=target))
        except Exception as e:
            return {"found": False, "error": str(e)}

    formatted_paths = []
    for path in paths:
        steps = []
        for idx in range(len(path)):
            curr_n = path[idx]
            curr_data = graph.nodes[curr_n]
            lbl = curr_data.get("label", curr_n)
            ntype = curr_data.get("node_type", "node")
            
            if idx < len(path) - 1:
                next_n = path[idx + 1]
                rel = "connects_to"
                if graph.has_edge(curr_n, next_n):
                    rel = graph[curr_n][next_n].get("relation", "connects_to")
                elif graph.has_edge(next_n, curr_n):
                    rel = f"is_{graph[next_n][curr_n].get('relation', 'affected_by')}_of"
                steps.append(f"[{ntype}] {lbl} ➔ --({rel})-->")
            else:
                steps.append(f"[{ntype}] {lbl}")

        formatted_paths.append({
            "hops": len(path) - 1,
            "nodes": [graph.nodes[n].get("label", n) for n in path],
            "trace": " ".join(steps)
        })

    return {
        "found": True,
        "source": graph.nodes[source].get("label", source),
        "target": graph.nodes[target].get("label", target),
        "total_paths": len(formatted_paths),
        "paths": formatted_paths
    }


def compute_blast_radius(graph: nx.DiGraph, target_id: str) -> Dict[str, Any]:
    """Calculates the ripple/blast radius of statutory reforms or doctrine changes."""
    if not graph.has_node(target_id):
        return {"found": False, "error": f"Node '{target_id}' not found."}

    data = graph.nodes[target_id]
    lbl = data.get("label", target_id)

    # 1st Degree: Direct dependencies (predecessors relying on this norm/concept)
    direct = set(graph.predecessors(target_id))
    if not direct:
        direct = set(graph.successors(target_id))

    direct_info = []
    for n in direct:
        ndata = graph.nodes[n]
        direct_info.append({
            "id": n,
            "label": ndata.get("label", n),
            "node_type": ndata.get("node_type", "node"),
            "source_work": ndata.get("obra", "")
        })

    # 2nd Degree: Cascading dependencies
    cascade = set()
    for d in direct:
        for succ in graph.successors(d):
            if succ != target_id and succ not in direct:
                cascade.add(succ)

    cascade_info = []
    for n in cascade:
        ndata = graph.nodes[n]
        cascade_info.append({
            "id": n,
            "label": ndata.get("label", n),
            "node_type": ndata.get("node_type", "node")
        })

    total = len(direct) + len(cascade)
    severity = "HIGH" if total >= 8 else ("MEDIUM" if total >= 3 else "LOW")

    return {
        "found": True,
        "target": lbl,
        "node_type": data.get("node_type"),
        "severity": severity,
        "metrics": {
            "direct_affected_g1": len(direct_info),
            "cascade_affected_g2": len(cascade_info),
            "total_entities_affected": total
        },
        "direct_affected": direct_info[:15],
        "cascade_affected": cascade_info[:15]
    }


def explain_node_360(graph: nx.DiGraph, node_id: str) -> Dict[str, Any]:
    """Generates a comprehensive 360-degree breakdown of a legal concept."""
    if not graph.has_node(node_id):
        return {"found": False, "error": f"Node '{node_id}' not found."}

    data = graph.nodes[node_id]
    out_edges = [(v, graph[node_id][v].get("relation", "")) for v in graph.successors(node_id)]

    statutes = [graph.nodes[v].get("label", v) for v, _ in out_edges if graph.nodes[v].get("node_type") == "articulo_legal"]
    case_law = [graph.nodes[v].get("label", v) for v, _ in out_edges if graph.nodes[v].get("node_type") == "jurisprudencia"]
    procedures = [graph.nodes[v].get("label", v) for v, _ in out_edges if graph.nodes[v].get("node_type") == "via_procesal"]
    concepts = [graph.nodes[v].get("label", v) for v, _ in out_edges if graph.nodes[v].get("node_type") == "institucion"]

    return {
        "found": True,
        "node_id": node_id,
        "label": data.get("label"),
        "node_type": data.get("node_type"),
        "area": data.get("area", "Law"),
        "author": data.get("autor", "Doctrine"),
        "work": data.get("obra", "Treatise"),
        "definition": data.get("definicion", ""),
        "procedural_framework": data.get("operativa_procesal", ""),
        "statutes": statutes,
        "case_law": case_law,
        "procedures": procedures,
        "related_concepts": concepts,
        "in_degree": graph.in_degree(node_id),
        "out_degree": graph.out_degree(node_id),
        "community": data.get("community", 0)
    }
