"""Architectural fact extraction: graph metrics and the principles built on them."""

from __future__ import annotations

from .graph import DependencyGraph, Edge, ModuleMetrics, build_graph
from .principle import Finding, Principle, PrincipleRegistry, principles

__all__ = [
    "DependencyGraph", "Edge", "ModuleMetrics", "build_graph",
    "Finding", "Principle", "PrincipleRegistry", "principles",
]
