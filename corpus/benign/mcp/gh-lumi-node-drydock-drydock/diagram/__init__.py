"""Mermaid diagram generation from architectural analysis.

Generates publication-ready dependency diagrams showing structure, coupling,
seams, and components. All output is deterministic and valid Mermaid syntax.
"""

from __future__ import annotations

from .mermaid import (
    component_diagram,
    layer_diagram,
    package_diagram,
    seam_diagram,
)

__all__ = [
    "layer_diagram",
    "package_diagram",
    "seam_diagram",
    "component_diagram",
]
