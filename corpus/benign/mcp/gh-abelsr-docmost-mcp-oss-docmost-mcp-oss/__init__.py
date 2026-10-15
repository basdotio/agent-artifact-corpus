"""MCP server (FastMCP) for Docmost."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

from .client import DocmostClient, DocmostError, DocmostMFARequired

__all__ = ["DocmostClient", "DocmostError", "DocmostMFARequired"]

try:
    # Single source of truth: the `version` field in pyproject.toml.
    __version__ = _distribution_version("docmost-mcp-oss")
except PackageNotFoundError:  # running from a checkout that is not installed
    __version__ = "0.0.0+unknown"
