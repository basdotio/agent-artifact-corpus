"""A process-wide map from MCP tool name to the capability its call requires.

The :func:`atlas_pca_fastmcp.pca_tool` decorator records a tool's requirement here so the middleware
can find it by the name that appears on a ``tools/call`` — without the middleware needing a reference
to the decorated function. An explicit ``tool_capability`` passed to :func:`pca_guard` always wins over
this registry.
"""
from typing import Dict, Optional

from .capability import Capability, parse_capability


class CapabilityRegistry:
    """A mutable ``tool name -> required Capability`` table."""

    def __init__(self) -> None:
        self._by_name: Dict[str, Capability] = {}

    def register(self, tool_name: str, requirement: str) -> Capability:
        cap = parse_capability(requirement)
        self._by_name[tool_name] = cap
        return cap

    def get(self, tool_name: str) -> Optional[Capability]:
        return self._by_name.get(tool_name)

    def clear(self) -> None:
        self._by_name.clear()


# The default registry the bare ``@pca_tool`` decorator and ``pca_guard`` share.
DEFAULT_REGISTRY = CapabilityRegistry()
