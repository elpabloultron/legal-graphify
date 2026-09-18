#!/usr/bin/env python
"""Reproduce — or refute — the token-compression numbers claimed in README.md.

Usage:
    python scripts/benchmark_token_savings.py

The README publishes a benchmark table (raw treatise context vs. LegalGraphify
subgraph, token reduction, compression ratio). This script measures what the
code actually produces for the same institutions, so the published figures can
be audited instead of taken on faith.

Two different notions of "raw context" exist in this project and they disagree:

  * ``tokens_completos`` — baked into the seed graph at ingest time as
    ``int(len(canonical_markdown.split()) * 1.3)``, i.e. the size of the
    *canonical* doctrine file, stored per institution.
  * the README's "Raw Treatise Context" column, which is hand-written.

The "subgraph" figure is ``int(len(yaml_ficha.split()) * 1.3)``: a word count of
the generated YAML, not a real tokenizer. Treat it as a proxy, not a measurement.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from legal_graphify.core.engine import LegalGraphEngine  # noqa: E402

# The five rows published in README.md ("Token Compression Benchmark").
README_CLAIMS = {
    "simulacion": ("Simulación de Contratos", 4200, 279),
    "cumplimiento forzado": ("Cumplimiento Forzado / Ejecución", 3850, 295),
    "responsabilidad extracontractual": ("Responsabilidad Extracontractual", 5100, 310),
    "nulidad de derecho publico": ("Nulidad de Derecho Público", 3400, 240),
    "imprevision": ("Teoría de la Imprevisión", 2900, 210),
}


def main() -> int:
    engine = LegalGraphEngine()
    print(f"Graph: {engine.graph.number_of_nodes()} nodes / {engine.graph.number_of_edges()} edges\n")

    header = (
        f"{'Institution':34} | {'README raw':>10} | {'README sub':>10} | {'README %':>8} | "
        f"{'actual raw':>10} | {'actual sub':>10} | {'actual %':>8} | {'actual x':>8}"
    )
    print(header)
    print("-" * len(header))

    for query, (label, readme_raw, readme_sub) in README_CLAIMS.items():
        res = engine.query_subgraph(query, max_hops=2)
        if not res.get("found"):
            print(f"{label:34} | {'NOT FOUND IN GRAPH':^62}")
            continue

        m = res["token_metrics"]
        actual_raw = m["raw_text_tokens"]
        actual_sub = m["subgraph_tokens"]
        readme_pct = round((1 - readme_sub / readme_raw) * 100, 1)
        actual_pct = m["savings_pct"]

        print(
            f"{label:34} | {readme_raw:>10} | {readme_sub:>10} | {readme_pct:>7.1f}% | "
            f"{actual_raw:>10} | {actual_sub:>10} | {actual_pct:>7.1f}% | {m['compression_ratio']:>8}"
        )

    print(
        "\nNote: 'actual raw' is the per-institution `tokens_completos` stored in the seed\n"
        "graph (canonical-file word count x1.3), NOT the raw treatise size quoted in the\n"
        "README table. The advertised 85%-95% band is not reproduced by the shipped data."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
