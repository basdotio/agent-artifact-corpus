"""
Entry point for running the MCP server as a module.
Usage: python -m src.mcp [base_url]
"""

import asyncio
import sys
from .server import main

if __name__ == "__main__":
    asyncio.run(main())