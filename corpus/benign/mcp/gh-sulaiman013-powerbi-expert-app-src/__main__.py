"""
Power BI MCP Server V3 - Module Entry Point

Run with: python -m src
Or: python -m src.server
"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())
