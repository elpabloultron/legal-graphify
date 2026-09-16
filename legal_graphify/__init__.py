"""
LegalGraphify — Multi-hop Knowledge Graph & Relational Reasoning Framework for Civil Law Systems.
Achieves 85%-95% LLM prompt token reduction via canonical ontological sub-graphs.
"""

from legal_graphify.core.engine import LegalGraphEngine
from legal_graphify.agents.doc2md_agent import Doc2MarkdownAgent

__version__ = "0.1.0"
__all__ = ["LegalGraphEngine", "Doc2MarkdownAgent", "__version__"]
