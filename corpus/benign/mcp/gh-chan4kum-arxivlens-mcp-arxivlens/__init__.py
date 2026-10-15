"""ArXivLens MCP: FastMCP 2.0 Server and Client for Real-Time Research Intelligence."""

__version__ = "0.1.0"
__author__ = "Chandan Kumar"

from arxivlens.client import ArXivLensClient
from arxivlens.models import CodeRepository, PaperMetadata, ResearchBrief
from arxivlens.server import mcp

__all__ = [
    "mcp",
    "ArXivLensClient",
    "PaperMetadata",
    "CodeRepository",
    "ResearchBrief",
]
