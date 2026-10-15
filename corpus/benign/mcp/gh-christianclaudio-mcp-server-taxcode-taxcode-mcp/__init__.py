"""Enterprise Model Context Protocol (MCP) server for Tax Code."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

from taxcode_mcp.ssrf import SSRFValidationError, validate_outbound_url

# The git tag is the version (uv-dynamic-versioning); never hard-code it here.
try:
    __version__ = _dist_version("mcp-server-taxcode")
except PackageNotFoundError:  # source tree without an installed distribution
    __version__ = "0.0.0"

__all__ = ["SSRFValidationError", "__version__", "validate_outbound_url"]
