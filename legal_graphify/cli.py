"""Command-line interface for LegalGraphify."""
import sys
import argparse
from legal_graphify.core.engine import LegalGraphEngine


def main():
    parser = argparse.ArgumentParser(
        prog="legal-graphify",
        description="⚖️ LegalGraphify — Knowledge Graph & Multi-hop Reasoning Framework for Civil Law Systems"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # query
    p_query = subparsers.add_parser("query", help="Extract dense ontological subgraph for an LLM prompt")
    p_query.add_argument("term", type=str, help="Legal concept or query string")
    p_query.add_argument("--hops", type=int, default=1, help="Relational hops radius (default: 1)")

    # path
    p_path = subparsers.add_parser("path", help="Find relational shortest paths between two legal entities")
    p_path.add_argument("source", type=str, help="Source legal concept or statute")
    p_path.add_argument("target", type=str, help="Target legal concept or statute")
    p_path.add_argument("--max-paths", type=int, default=3, help="Max paths to return (default: 3)")

    # explain
    p_explain = subparsers.add_parser("explain", help="360-degree comprehensive inspection of an entity")
    p_explain.add_argument("term", type=str, help="Legal concept to explain")

    # affected
    p_affected = subparsers.add_parser("affected", help="Blast radius / impact analysis of statutory reform")
    p_affected.add_argument("term", type=str, help="Statute or concept being reformed")

    # god-nodes
    p_god = subparsers.add_parser("god-nodes", help="Identify architectural pillars (God Nodes) via PageRank")
    p_god.add_argument("--top", type=int, default=10, help="Top N entities to display (default: 10)")

    # mermaid
    p_mermaid = subparsers.add_parser("mermaid", help="Render Mermaid syntax diagram for an entity")
    p_mermaid.add_argument("term", type=str, help="Central legal concept")
    p_mermaid.add_argument("--hops", type=int, default=1, help="Neighborhood radius")

    # stats
    subparsers.add_parser("stats", help="Show global graph topology metrics")

    # serve
    subparsers.add_parser("serve", help="Run standalone Model Context Protocol (MCP) server")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    engine = LegalGraphEngine()

    if args.subcommand == "stats":
        g = engine.graph
        print(f"📊 LegalGraphify Topology Metrics:")
        print(f"  • Total Nodes: {g.number_of_nodes()}")
        print(f"  • Total Edges: {g.number_of_edges()}")
        return

    if args.subcommand == "query":
        res = engine.query_subgraph(args.term, max_hops=args.hops)
        if not res.get("found"):
            print(f"⚠️ {res.get('message')}")
            return
        m = res["token_metrics"]
        print("\n🧠 LEGAL SUBGRAPH (YAML Context):")
        print("═" * 60)
        print(res["subgraph_yaml"])
        print("═" * 60)
        print(f"⚡ Token Compression: {m['compression_ratio']} ({m['savings_pct']}% saved | {m['raw_text_tokens']} ➔ {m['subgraph_tokens']} tokens)\n")
        return

    if args.subcommand == "path":
        res = engine.path(args.source, args.target, max_paths=args.max_paths)
        if not res.get("found"):
            print(f"⚠️ {res.get('message') or res.get('error')}")
            return
        print(f"\n🛤️ Relational Paths: '{res['source']}' ➔ '{res['target']}'")
        print("═" * 70)
        for idx, p in enumerate(res["paths"], 1):
            print(f"Route {idx} ({p['hops']} hops):")
            print(f"  {p['trace']}\n")
        print("═" * 70)
        return

    if args.subcommand == "explain":
        res = engine.explain(args.term)
        if not res.get("found"):
            print(f"⚠️ {res.get('message') or res.get('error')}")
            return
        print(f"\n# 🏛️ Dogmatic Breakdown: {res['label']}")
        print(f"**Area:** {res['area']} | **Author:** {res['author']} | **Work:** {res['work']}")
        print(f"\n### Definition:\n{res['definition'] or 'Not registered'}")
        print(f"\n### Procedural Framework:\n{res['procedural_framework'] or 'General declarative action'}")
        print("\n### Statutes (BCN):")
        for s in res['statutes'][:6]:
            print(f"  - {s}")
        print("\n### Precedents (Supreme Court):")
        for c in res['case_law'][:4]:
            print(f"  - {c}")
        print("\n### Procedural Actions:")
        for p in res['procedures'][:4]:
            print(f"  - {p}")
        return

    if args.subcommand == "affected":
        res = engine.affected(args.term)
        if not res.get("found"):
            print(f"⚠️ {res.get('message') or res.get('error')}")
            return
        print(f"\n💥 Blast Radius Analysis: {res['target']}")
        print("═" * 60)
        print(f"Severity:                {res['severity']}")
        print(f"Direct Affected (G1):    {res['metrics']['direct_affected_g1']}")
        print(f"Cascade Affected (G2):   {res['metrics']['cascade_affected_g2']}")
        print(f"Total Entities at Risk:  {res['metrics']['total_entities_affected']}")
        print("\nDirect Impact Nodes:")
        for item in res["direct_affected"]:
            print(f"  • [{item['node_type']}] {item['label']} ({item.get('source_work', '')})")
        print("═" * 60)
        return

    if args.subcommand == "god-nodes":
        res = engine.god_nodes(top_n=args.top)
        print(f"\n🏛️ Pillars of Civil Law (God Nodes - PageRank Top {args.top}):")
        print("═" * 70)
        print("Foundational Legal Institutions:")
        for idx, item in enumerate(res["god_institutions"], 1):
            print(f"  {idx:2d}. {item['label']:<40} | PR: {item['pagerank']:.5f} | Degree: {item['degree']}")
        print("\nFoundational Statutes (BCN):")
        for idx, item in enumerate(res["god_statutes"], 1):
            print(f"  {idx:2d}. {item['label']:<40} | PR: {item['pagerank']:.5f} | Degree: {item['degree']}")
        print("═" * 70)
        return

    if args.subcommand == "mermaid":
        print(engine.mermaid(args.term, hops=args.hops))
        return

    if args.subcommand == "serve":
        from legal_graphify.mcp.server import run_mcp_server
        run_mcp_server()


if __name__ == "__main__":
    main()
