# 🏛️ Arquitectura del Sistema LegalGraphify

> **Framework Ontológico de Grafos de Conocimiento y Razonamiento Relacional Multiruta para Sistemas de Derecho Continental (*Civil Law*).**
> Diseñado bajo la premisa de **Ahorro Radical de Tokens (85 % - 95 %)**, **Cero Alucinaciones Relacionales** y **Asimilación Continua de Doctrina y Jurisprudencia**.

---

## 📐 1. Motivación y Principios Técnicos

En sistemas jurídicos de tradición romano-germánica o continental (como el chileno), el razonamiento forense es primordialmente deductivo, normativo y jerárquico. El enfoque convencional de **Vector RAG** (embeddings densos y similitud de coseno) presenta graves deficiencias:
1. **Pérdida de Jerarquía Normativa:** La cercanía semántica confunde una regla general con su excepción legal expresa (ej. Art. 1464 CC vs. excepciones del CPC).
2. **Cadenas de Subsunción Rotas:** Un LLM no puede trazar inductivamente cómo una *Simulación Ilícita* deviene en *Inoponibilidad* y de ahí a *Acción Pauliana*.
3. **Explosión de la Ventana de Contexto:** Inyectar tratados y códigos enteros consume decenas de miles de tokens por turno, encareciendo y ralentizando las consultas.

**LegalGraphify** resuelve este problema construyendo un grafo dirigido ponderado multidimensional $G = (V, E)$ donde los nodos representan conceptos dogmáticos, normas estatutarias, fallos de la Corte Suprema y autores canónicos, y las aristas representan relaciones jurídicas tipificadas.

---

## 🏗️ 2. Topología del Grafo y Tipos de Entidades

### Nodos ($V$):
* `institucion`: Fichas dogmáticas unificadas (definición, requisitos, operativa procesal forense).
* `norma`: Artículos del Código Civil, Código de Comercio, leyes especiales de la BCN y CPR.
* `jurisprudencia`: Sentencias y roles de la Excma. Corte Suprema, Cortes de Apelaciones y Tribunal Constitucional.
* `autor`: Tratadistas canónicos (Vial del Río, Ramos Pazos, Barros Bourie, Peñailillo, Bermúdez, Cury, etc.).
* `concepto`: Sub-elementos fácticos o presupuestos jurídicos (culpa, dolo, daño emergente, lucro cesante).

### Aristas Relacionales ($E$):
* `regulado_por`: Vincula una institución con su base legal en la ley positiva.
* `sanciona_con`: Vincula una transgresión con una sanción procesal o sustantiva (ej. *Objeto Ilícito* $\rightarrow$ *Nulidad Absoluta*).
* `exige`: Especifica presupuestos o requisitos copulativos para la procedencia de una acción.
* `excepciona`: Define causales de exención o contra-excepciones procesales.
* `criterio_rector_de`: Conecta fallos de casación con la interpretación vinculante de la institución.
* `analizado_por`: Identifica la doctrina dogmática que sistematiza la materia.

---

## ⚡ 3. Los 6 Modos de Inferencia

```
┌────────────────────────────────────────────────────────────────────────┐
│                        LEGALGRAPHIFY ENGINE                            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
    ┌──────────────┬────────────────┼──────────────┬─────────────┐
    ▼              ▼                ▼              ▼             ▼
┌───────┐    ┌──────────┐    ┌─────────────┐  ┌──────────┐  ┌───────────┐
│ query │    │   path   │    │   explain   │  │ affected │  │ god-nodes │
└───────┘    └──────────┘    └─────────────┘  └──────────┘  └───────────┘
    │              │                │              │             │
    ▼              ▼                ▼              ▼             ▼
 Subgrafo       Camino           Ficha 360°      Radio de     PageRank
  Ego N       Deductivo         Definición +    Afectación   Centralidad
  Saltos       Mínimo            BCN + Fallo     Cascada       Pilares
                                                                  ▲
                                                                  │
                                                        ┌─────────────────┐
                                                        │     ingest      │
                                                        │ Doc2Markdown    │
                                                        │ Normalizador    │
                                                        │ RAE / BCN / CS  │
                                                        └─────────────────┘
```

1. **`query(institucion, depth)`:** Extrae el subgrafo ego centrado en la entidad a $N$ saltos en YAML hiper-denso (~150-250 tokens), logrando una reducción del 85 % al 95 % de tokens.
2. **`path(origen, destino)`:** Calcula los caminos deductivos más cortos entre dos conceptos mediante Dijkstra/BFS, explicando la relación de causalidad dogmática.
3. **`explain(institucion)`:** Emite la ficha 360° con su definición canónica, concordancias BCN, fallos rectores de la Corte Suprema y vías procesales de ejercicio.
4. **`affected(norma_o_concepto)`:** Evalúa el radio de afectación sistémico (*blast radius*) de una reforma estatutaria o giro jurisprudencial en Grado 1 y Grado 2.
5. **`god-nodes(top_n)`:** Emplea algoritmos de centralidad de intermediación y PageRank para identificar los pilares estructurales del derecho positivo.
6. **`ingest(archivo, actualizar_grafo)`:** Pipeline autónomo ejecutado por `Doc2MarkdownAgent` que extrae texto crudo (PDF, DOCX, TXT), repara saltos espurios, impone normas ortotipográficas RAE/ASALE, estandariza citas oficiales BCN y asimila en caliente nuevos nodos al grafo.

---

## 🔌 4. Integración FastMCP

LegalGraphify expone su funcionalidad mediante el protocolo estándar MCP (*Model Context Protocol*):

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

### Herramientas MCP Nativas:
* `query_legal_subgraph`
* `trace_legal_path`
* `explain_legal_entity`
* `analyze_statutory_impact`
* `get_god_nodes`
* `ingest_document_to_markdown`

---

## 🧪 5. Pruebas y Certificación de Calidad

* Suite completa de pruebas con `pytest`: **16/16 pruebas aprobadas (100 % de éxito)**.
* Cobertura de grafos, algoritmos de centralidad, inferencia relacional, normalización ortotipográfica RAE, parsing de citas BCN/CS y herramientas FastMCP.
