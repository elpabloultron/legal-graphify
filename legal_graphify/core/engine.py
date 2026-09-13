"""Core LegalGraphify Engine."""
import os
import json
from typing import Dict, Any, Optional, List, Set
from pathlib import Path
import networkx as nx

from legal_graphify.extractors.doctrine import normalize_str, sanitize_id, extract_doctrine_directory
from legal_graphify.core.centrality import compute_pagerank, detect_communities, extract_god_nodes
from legal_graphify.core.reasoning import find_shortest_paths, compute_blast_radius, explain_node_360
from legal_graphify.visualizer.mermaid import generate_mermaid


DEFAULT_SEED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "legal_knowledge_graph.json")


class LegalGraphEngine:
    """High-performance Legal Knowledge Graph Engine for Civil Law & Statutory Systems."""

    def __init__(self, graph_path: Optional[str] = None):
        self.graph = nx.DiGraph()
        self.instituciones_index: Dict[str, str] = {}
        self.normas_index: Dict[str, str] = {}
        self.is_built = False
        self.graph_path = graph_path or DEFAULT_SEED_PATH

        if os.path.exists(self.graph_path):
            self.load_graph_json(self.graph_path)

    def load_graph_json(self, filepath: str) -> bool:
        """Loads serialized graph from Node-Link JSON."""
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "edges" in data and "links" not in data:
                data["links"] = data["edges"]
            elif "links" in data and "edges" not in data:
                data["edges"] = data["links"]

            loaded = None
            for edges_key in [None, "edges", "links"]:
                try:
                    kwargs = {"directed": True}
                    if edges_key:
                        kwargs["edges"] = edges_key
                    g = nx.node_link_graph(data, **kwargs)
                    if g.number_of_nodes() > 0:
                        loaded = g
                        break
                except Exception:
                    continue

            if loaded is not None:
                self.graph = loaded
                self._rebuild_indices()
                self.is_built = True
                return True
        except Exception:
            pass
        return False

    def save_graph_json(self, filepath: Optional[str] = None) -> str:
        """Persists graph to Node-Link JSON format."""
        target = filepath or self.graph_path
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            data = nx.node_link_data(self.graph, edges="edges")
        except Exception:
            data = nx.node_link_data(self.graph)

        if "edges" in data and "links" not in data:
            data["links"] = data["edges"]
        elif "links" in data and "edges" not in data:
            data["edges"] = data["links"]

        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return target

    def _rebuild_indices(self) -> None:
        """Refreshes lookup indices for fast search."""
        self.instituciones_index.clear()
        self.obras_index = {}
        self.normas_index.clear()
        for nid, d in self.graph.nodes(data=True):
            lbl = normalize_str(d.get("label", ""))
            ntype = d.get("node_type")
            if ntype == "institucion":
                self.instituciones_index[lbl] = nid
            elif ntype == "obra":
                self.obras_index[lbl] = nid
            elif ntype == "articulo_legal":
                self.normas_index[lbl] = nid

    def find_node(self, query: str) -> Optional[str]:
        """Resolves natural language or citation string to a graph node ID."""
        q_norm = normalize_str(query)
        
        # 1. Exact match in institutions
        for name, nid in self.instituciones_index.items():
            if q_norm == name:
                return nid

        # 2. Substring match in institutions
        for name, nid in self.instituciones_index.items():
            if q_norm in name:
                return nid

        # 3. Match in statutes
        for name, nid in self.normas_index.items():
            if q_norm in name:
                preds = list(self.graph.predecessors(nid))
                if preds:
                    return preds[0]
                return nid

        # 4. Match in treatises (obras)
        for name, nid in getattr(self, "obras_index", {}).items():
            if q_norm in name:
                return nid

        # 5. Fuzzy overlap
        words = [w for w in q_norm.split() if len(w) > 3]
        best_node = None
        max_score = 0
        for nid, data in self.graph.nodes(data=True):
            lbl = normalize_str(data.get("label", ""))
            weight = 10 if data.get("node_type") == "institucion" else 2
            score = sum(weight for w in words if w in lbl)
            if score > max_score:
                max_score = score
                best_node = nid
        return best_node

    def query_subgraph(self, query: str, max_hops: int = 1) -> Dict[str, Any]:
        """Extracts dense ego-subgraph and calculates token savings."""
        center_id = self.find_node(query)
        if not center_id or not self.graph.has_node(center_id):
            return {
                "found": False,
                "query": query,
                "message": f"No dogmatic node found for '{query}'.",
                "suggestions": list(self.instituciones_index.keys())[:5]
            }

        center = self.graph.nodes[center_id]
        sub_nodes = {center_id}
        current_layer = {center_id}
        for _ in range(max_hops):
            nxt = set()
            for n in current_layer:
                nxt.update(self.graph.successors(n))
                nxt.update(self.graph.predecessors(n))
            sub_nodes.update(nxt)
            current_layer = nxt

        normas, fallos, vias = [], [], []
        for n in sub_nodes:
            if n == center_id:
                continue
            t = self.graph.nodes[n].get("node_type")
            lbl = self.graph.nodes[n].get("label", n)
            if t == "articulo_legal":
                normas.append(lbl)
            elif t == "jurisprudencia":
                fallos.append(lbl)
            elif t == "via_procesal":
                vias.append(lbl)

        autor_obra = f"{center.get('autor', 'Doctrina')} — {center.get('obra', 'Tratado')}"
        ficha_yaml = (
            f"institucion: \"{center.get('label')}\"\n"
            f"area: \"{center.get('area', 'Derecho')}\"\n"
            f"fuente_canonica: \"{autor_obra}\"\n"
            f"definicion: \"{center.get('definicion', 'No registrada')}\"\n"
            f"normas_positivas: {json.dumps(normas[:6], ensure_ascii=False)}\n"
            f"criterios_cs: {json.dumps(fallos[:3], ensure_ascii=False)}\n"
            f"operativa_procesal: \"{center.get('operativa_procesal', vias[0] if vias else 'Vía ordinaria declarativa')}\""
        )

        tokens_subgrafo = int(len(ficha_yaml.split()) * 1.3)
        tokens_completos = center.get("tokens_completos", 2800)
        ahorro = max(0, tokens_completos - tokens_subgrafo)
        pct = round((ahorro / max(1, tokens_completos)) * 100, 1)

        return {
            "found": True,
            "node_id": center_id,
            "label": center.get("label"),
            "subgraph_yaml": ficha_yaml,
            "token_metrics": {
                "subgraph_tokens": tokens_subgrafo,
                "raw_text_tokens": tokens_completos,
                "tokens_saved": ahorro,
                "savings_pct": pct,
                "compression_ratio": f"{round(tokens_completos / max(1, tokens_subgrafo), 1)}x"
            },
            "subgraph_stats": {
                "nodes_in_subgraph": len(sub_nodes),
                "statutes_connected": len(normas),
                "rulings_connected": len(fallos),
                "procedures_connected": len(vias)
            }
        }

    def path(self, source: str, target: str, max_paths: int = 3) -> Dict[str, Any]:
        """Traces the shortest reasoning path between two entities."""
        src_id = self.find_node(source)
        tgt_id = self.find_node(target)
        if not src_id or not tgt_id:
            return {"found": False, "message": f"Could not resolve '{source}' or '{target}'."}
        return find_shortest_paths(self.graph, src_id, tgt_id, max_paths=max_paths)

    def explain(self, query: str) -> Dict[str, Any]:
        """Provides a 360-degree explanation of a node."""
        node_id = self.find_node(query)
        if not node_id:
            return {"found": False, "message": f"Could not resolve '{query}'."}
        return explain_node_360(self.graph, node_id)

    def affected(self, statute_or_concept: str) -> Dict[str, Any]:
        """Analyzes the blast radius of a statutory reform or doctrinal change."""
        node_id = self.find_node(statute_or_concept)
        if not node_id:
            return {"found": False, "message": f"Could not resolve '{statute_or_concept}'."}
        return compute_blast_radius(self.graph, node_id)

    def god_nodes(self, top_n: int = 10) -> Dict[str, Any]:
        """Computes structural pillar entities (God Nodes) using PageRank."""
        return extract_god_nodes(self.graph, top_n=top_n)

    def mermaid(self, query: str, hops: int = 1) -> str:
        """Exports Mermaid visual diagram string."""
        node_id = self.find_node(query)
        if not node_id:
            return "```mermaid\ngraph TD\n    A[\"Node not found\"]\n```"
        return generate_mermaid(self.graph, node_id, max_hops=hops)
