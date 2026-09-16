<p align="center">
  <h1 align="center">⚖️ LegalGraphify</h1>
  <p align="center"><strong>Knowledge Graph & Multi-hop Relational Reasoning Framework for Civil Law Systems</strong></p>
  <p align="center"><em>85%–95% LLM Prompt Token Savings via Canonical Ontological Sub-graphs</em></p>
</p>

<p align="center">
  <a href="https://github.com/elpabloultron/legal-graphify/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg" alt="Python Versions">
  <img src="https://img.shields.io/badge/MCP-Compatible-green.svg" alt="MCP Compatible">
  <img src="https://img.shields.io/badge/NetworkX-3.0%2B-orange.svg" alt="NetworkX">
</p>

---

## 🎯 Overview

**LegalGraphify** is an open-source knowledge graph engine tailored for statutory and civil law systems (*Civil Law / Continental Law*), inspired by the AST-driven architecture of [Graphify](https://github.com/Graphify-Labs/graphify).

Standard vector RAG (*Retrieval-Augmented Generation*) frequently breaks down in legal reasoning:
1. **Context Window Bloat:** Feeding 800-page civil law treatises, statutory codes (thousands of articles), and supreme court rulings into prompts quickly exhausts context limits or incurs unsustainable inference costs.
2. **Relational Hallucinations:** Vector cosine similarity cannot reliably differentiate between an *essential requirement*, an *evidentiary presumption*, a *statutory exception*, and a *prescription deadline*.

**LegalGraphify** indexes statutory codes (BCN), doctrinal treatises, and Supreme Court case law into an auditable, multi-hop relational graph. Instead of dumping raw chapters into prompts, it extracts canonical, localized ego-subgraphs at $N$ hops—slashing prompt token overhead by **85% to 95%** while guaranteeing 100% relational fidelity.

---

## ⚡ Token Compression Benchmark

| Legal Institution / Doctrine | Raw Treatise Context | LegalGraphify Subgraph (2 hops) | Token Reduction | Compression Ratio |
| :--- | :---: | :---: | :---: | :---: |
| **Simulación de Contratos** | ~4,200 tokens | **279 tokens** | **93.4%** | **15.0x** |
| **Cumplimiento Forzado / Ejecución** | ~3,850 tokens | **295 tokens** | **92.3%** | **13.0x** |
| **Responsabilidad Extracontractual** | ~5,100 tokens | **310 tokens** | **93.9%** | **16.5x** |
| **Nulidad de Derecho Público** | ~3,400 tokens | **240 tokens** | **92.9%** | **14.1x** |
| **Teoría de la Imprevisión** | ~2,900 tokens | **210 tokens** | **92.7%** | **13.8x** |

---

## 🚀 Key Capabilities

### 1. Multi-hop Relational Path Tracing (`legal-graphify path`)
Trace the exact deductive chain between any two distant legal institutions or statutory articles:
```bash
$ legal-graphify path "simulacion" "nulidad"
```
```text
🛤️ Relational Paths: 'La Simulación de los Actos Jurídicos' ➔ 'Régimen Jurídico de la Nulidad Civil'
══════════════════════════════════════════════════════════════════════
Route 1 (2 hops):
  [institucion] La Simulación de los Actos Jurídicos ➔ --(analizado_por)--> [autor] Víctor Vial del Río ➔ --(is_analizado_por_of)--> [institucion] Régimen Jurídico de la Nulidad Civil
```

### 2. $360^\circ$ Dogmatic Explanation (`legal-graphify explain`)
Generates an exhaustive diagnostic sheet with statutory bases (BCN), Supreme Court case law, procedural remedies, and network centrality:
```bash
$ legal-graphify explain "simulacion"
```

### 3. Blast Radius & Statutory Impact Analysis (`legal-graphify affected`)
Calculates cascading risks when a statute is reformed or a judicial precedent changes:
```bash
$ legal-graphify affected "Art. 2515 CC"
```
```text
💥 Blast Radius Analysis: Cumplimiento Forzado de las Obligaciones
Severity:                HIGH
Direct Affected (G1):    2
Cascade Affected (G2):   22
Total Entities at Risk:  24
```

### 4. Structural Pillar Detection (`legal-graphify god-nodes`)
Identifies foundational institutions and core statutory articles using PageRank and betweenness centrality:
```bash
$ legal-graphify god-nodes --top 5
```

### 5. Instant Visual Diagrams (`legal-graphify mermaid`)
Generates styled Mermaid diagrams directly in your terminal for Markdown rendering.

### 6. Autonomous Doc2Markdown & Graph Ingestion (`legal-graphify ingest`)
Transforms messy legal texts or documents (`.pdf`, `.docx`, `.txt`, `.md`) into canonical, token-optimized Markdown according to RAE/ASALE standards, Chilean statutory citation formats (`[BCN - Código Civil, Art. 1437]`, `[CS - Rol N° 1234-2023]`), and incrementally assimilates newly discovered institutions into the knowledge graph:
```bash
$ legal-graphify ingest "tratado_imprevision.pdf" --output "doctrina/civil/imprevision.md" --update-graph
```

---

## 📦 Installation

```bash
# Clone and install locally
git clone https://github.com/elpabloultron/legal-graphify.git
cd legal-graphify
pip install -e .

# Or install with MCP server support
pip install -e ".[mcp]"
```

---

## 🔌 Model Context Protocol (MCP) Integration

LegalGraphify provides a native MCP server for integration with **Claude Desktop**, **Cursor**, and **Gemini**:

```json
{
  "mcpServers": {
    "legal-graphify": {
      "command": "legal-graphify",
      "args": ["serve"]
    }
  }
}
```

### Exposed MCP Tools:
- `query_legal_subgraph(query, hops)`: Scoped YAML sub-graph for prompt context (85%–95% savings).
- `trace_legal_path(source, target)`: Relational reasoning chains between legal entities.
- `explain_legal_entity(query)`: $360^\circ$ breakdown (statutes, case law, actions).
- `analyze_statutory_impact(statute_or_concept)`: Legislative/case-law blast radius.
- `get_god_nodes(top_n)`: PageRank structural pillars.
- `ingest_document_to_markdown(source_text_or_path, output_path, update_graph)`: Ingests raw text or documents, normalizes to canonical RAE/Chilean legal Markdown, and incrementally assimilates nodes and relations into the active knowledge graph.

---

## 💻 Python API Usage

```python
from legal_graphify import LegalGraphEngine, Doc2MarkdownAgent

# Initialize engine (loads bundled seed knowledge graph)
engine = LegalGraphEngine()

# 1. Query scoped subgraph
subgraph = engine.query_subgraph("simulacion", max_hops=1)
print(subgraph["subgraph_yaml"])
print(f"Tokens saved: {subgraph['token_metrics']['savings_pct']}%")

# 2. Trace reasoning path
path_result = engine.path("simulacion", "nulidad")
print(path_result["paths"][0]["trace"])

# 3. Analyze blast radius
impact = engine.affected("Art. 2515 CC")
print(f"Risk level: {impact['severity']}")

# 4. Autonomous document ingestion & graph assimilation
agent = Doc2MarkdownAgent(engine=engine)
result = agent.run(
    source="tratado_imprevision.pdf",
    output_path="doctrina/imprevision.md",
    update_graph=True,
    default_author="Jorge López Santa María",
    default_area="Derecho Civil Patrimonial"
)
print(f"Ingested {result['institutions_count']} institutions, new nodes: {result['assimilation']['nodes_added']}")
```

---

## 🌐 Ecosystem & Acknowledgments

- **Open Legal Chile:** Born as the knowledge-graph core of [Open Legal Chile](https://github.com/elpabloultron/open-legal-chile).
- **Graphify Labs:** Conceptually inspired by [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify).

---

## 📜 License

MIT License © 2026 Pablo Benavides Jorquera.
