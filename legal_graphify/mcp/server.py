"""Standalone Model Context Protocol (MCP) Server for LegalGraphify."""
import json
from typing import Dict, Any, Optional

try:
    from fastmcp import FastMCP
    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False

from legal_graphify.core.engine import LegalGraphEngine


def create_mcp_app():
    if not HAS_FASTMCP:
        raise ImportError("fastmcp is required to run the MCP server. Install with 'pip install fastmcp'.")

    mcp = FastMCP("legal-graphify")
    engine = LegalGraphEngine()

    @mcp.tool()
    def query_legal_subgraph(query: str, hops: int = 1) -> str:
        """Extract a dense ontological legal subgraph (85%-95% token savings) for prompt injection."""
        res = engine.query_subgraph(query, max_hops=hops)
        if not res.get("found"):
            return f"Concept '{query}' not found."
        return res["subgraph_yaml"]

    @mcp.tool()
    def trace_legal_path(source: str, target: str, max_paths: int = 3) -> Dict[str, Any]:
        """Find the relational chain and shortest reasoning path between two legal entities."""
        return engine.path(source, target, max_paths=max_paths)

    @mcp.tool()
    def explain_legal_entity(query: str) -> Dict[str, Any]:
        """Get an exhaustive 360-degree breakdown of a legal concept, including statutes, case law, and procedures."""
        return engine.explain(query)

    @mcp.tool()
    def analyze_statutory_impact(statute_or_concept: str) -> Dict[str, Any]:
        """Calculate the blast radius and cascading impact when a statute or doctrine changes."""
        return engine.affected(statute_or_concept)

    @mcp.tool()
    def get_god_nodes(top_n: int = 10) -> Dict[str, Any]:
        """Identify foundational legal pillars and statutes using PageRank centrality."""
        return engine.god_nodes(top_n=top_n)

    return mcp


def run_mcp_server():
    mcp = create_mcp_app()
    mcp.run()


if __name__ == "__main__":
    run_mcp_server()
