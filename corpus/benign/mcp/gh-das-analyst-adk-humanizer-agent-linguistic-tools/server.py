"""FastMCP Server providing linguistic diagnostics and text diff comparisons."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastmcp import FastMCP
from tools.metrics import analyze_linguistic_metrics as _analyze_metrics
from tools.diff import compare_texts as _compare_texts

# Initialize FastMCP Server
mcp = FastMCP("linguistic-tools-server")


@mcp.tool()
def analyze_linguistic_metrics(text: str) -> Dict[str, Any]:
    """Analyze input text for Large Language Model markers, sentence burstiness, predictability, and clichés.

    Args:
        text: The prose to inspect.

    Returns:
        A dictionary containing sentence metrics, burstiness standard deviation,
        cliché count/tokens, opener diversity, and composite Human-Likeness Index.
    """
    return _analyze_metrics(text)


@mcp.tool()
def compare_texts(original_text: str, humanized_text: str) -> Dict[str, Any]:
    """Compare original and humanized text, analyzing linguistic metric improvements and changes.

    Args:
        original_text: The starting text before rewriting.
        humanized_text: The rewritten prose.

    Returns:
        A dictionary with before/after metrics, HLI delta, burstiness improvement,
        clichés removed, and improvement highlights.
    """
    return _compare_texts(original_text, humanized_text)


if __name__ == "__main__":
    mcp.run()
