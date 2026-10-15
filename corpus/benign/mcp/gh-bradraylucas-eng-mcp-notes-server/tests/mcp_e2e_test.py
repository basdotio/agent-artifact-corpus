#!/usr/bin/env python3
"""End-to-end MCP protocol test: launches server.py over stdio with the real
mcp SDK (v1.x) and calls all three tools. Requires: pip install "mcp>=1.6.0,<2"
Usage: python tests/mcp_e2e_test.py"""
import asyncio, json, os, shutil, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    workdir = "/tmp/mcp_e2e"
    shutil.rmtree(workdir, ignore_errors=True); os.makedirs(workdir)
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server.py"), workdir + "/server.py")
    params = StdioServerParameters(command=sys.executable, args=[workdir + "/server.py"], cwd=workdir)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print("TOOLS:", names)
            r1 = await session.call_tool("create_note", {"title": "Shopping list", "body": "milk, eggs, coffee"})
            print("CREATE:", r1.content[0].text[:120])
            r2 = await session.call_tool("search_notes", {"query": "EGGS"})
            print("SEARCH hits contain 'Shopping list':", "Shopping list" in r2.content[0].text)
            r3 = await session.call_tool("list_notes", {"limit": 5})
            print("LIST contains both fields:", "Shopping list" in r3.content[0].text)
            assert names == ["create_note", "list_notes", "search_notes"], names
            print("E2E MCP PROTOCOL TEST: PASS")

asyncio.run(main())
