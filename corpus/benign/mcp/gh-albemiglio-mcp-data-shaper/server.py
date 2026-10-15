#!/usr/bin/env python3
"""
mcp-data-shaper  —  LLM-powered CSV labeling as an MCP server
==========================================================

Validates, corrects, and enriches labels in any CSV dataset by sending
rows in parallel batches to an LLM and collecting only the rows that need
to change, together with a reasoning field.

Supported tasks: label correction, content classification, entity extraction,
content moderation, quality evaluation, fact checking, data enrichment, and
any custom validation expressible as a natural-language prompt.

Transport   : MCP stdio
Providers   : OpenAI (OPENAI_API_KEY) · Gemini (GEMINI_API_KEY)

See the ``datashaper`` package for the core implementation:
  datashaper/models.py  — Pydantic output models
  datashaper/llm.py     — LLM provider abstraction
  datashaper/labeler.py — GenericLabeler engine
  datashaper/tools.py   — MCP tool definitions and handlers
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from datashaper.tools import TOOLS, handle_call_tool

# ---------------------------------------------------------------------------
# Logging — always to stderr; stdout is reserved for MCP JSON-RPC frames
# ---------------------------------------------------------------------------

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[data-shaper] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

app = Server("mcp-data-shaper")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    return await handle_call_tool(name, arguments)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    logger.info("mcp-data-shaper ready. Tools: %s", [t.name for t in TOOLS])
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
