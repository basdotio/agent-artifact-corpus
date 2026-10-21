"""``src/mcp_prompts`` — USER-facing MCP prompts (workflow recipes for prompts/list and
prompts/get).

This package is distinct from ``src/llm.py``, which holds the INTERNAL LLM prompt
content (structured-output field specs and calibration anchors for the pipeline's
four LLM call kinds). Everything here is rendered to the MCP client on demand.
"""

from src.mcp_prompts.workflows import register_prompts

__all__ = ["register_prompts"]
