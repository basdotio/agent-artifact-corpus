"""mcp-forge: production-ready Model Context Protocol servers in Python.

Zero dependencies, one import::

    from mcp_forge import Server
"""

from .runtime import PROTOCOL_VERSIONS, Server, Tool, ToolError, log
from .validate import SchemaError, check, validate

__version__ = "1.0.0"

__all__ = [
    "Server",
    "Tool",
    "ToolError",
    "SchemaError",
    "PROTOCOL_VERSIONS",
    "log",
    "check",
    "validate",
    "__version__",
]
