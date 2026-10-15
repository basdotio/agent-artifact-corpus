"""Plane MCP server — expose the Plane REST API over the Model Context Protocol."""

from .client import PlaneAPIError, PlaneClient
from .config import ConfigError, Settings

__all__ = ["PlaneAPIError", "PlaneClient", "ConfigError", "Settings", "__version__"]

__version__ = "0.1.0"
