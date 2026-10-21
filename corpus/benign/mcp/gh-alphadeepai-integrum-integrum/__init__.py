"""Integrum: Expose any Python module or library as an MCP server."""

from integrum.filter import MemberFilter
from integrum.inspector import import_target, inspect_class, inspect_function, inspect_module
from integrum.server import IntegrumServer
from integrum.store import ObjectStore, WordIdGenerator

__version__ = "0.1.0"

__all__ = [
    "IntegrumServer",
    "ObjectStore",
    "WordIdGenerator",
    "MemberFilter",
    "import_target",
    "inspect_class",
    "inspect_function",
    "inspect_module",
]
