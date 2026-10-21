"""Integration test: connect as a real MCP client over stdio."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
import unittest

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parent.parent


async def check_protocol():
    server = StdioServerParameters(
        command=sys.executable,
        args=["-u", str(ROOT / "talkpipe_mcp.py")],
        cwd=str(ROOT),
    )
    async with stdio_client(server) as (reader, writer):
        async with ClientSession(reader, writer) as client:
            init = await client.initialize()
            assert "talkpipe" in init.serverInfo.name, init.serverInfo
            declared = await client.list_tools()
            names = {tool.name for tool in declared.tools}
            assert names == {"talkpipe_run", "talkpipe_capabilities"}, names
            assert all(t.annotations.readOnlyHint is True and t.annotations.destructiveHint is False for t in declared.tools)

            cap = await client.call_tool("talkpipe_capabilities")
            assert not cap.isError, cap
            normalize = await client.call_tool(
                "talkpipe_run",
                {"workflow": "normalize", "items": ["   From  this   chat  ", " TalkPipe  "]},
            )
            assert not normalize.isError, normalize
            data = normalize.structuredContent
            if data and "result" in data:
                data = data["result"]
            if not data or "results" not in data:
                data = json.loads(normalize.content[0].text)
            assert data["results"] == ["From this chat", "TalkPipe"], data

            bad = await client.call_tool(
                "talkpipe_run", {"workflow": "shell", "items": ["echo blocked"]}
            )
            assert bad.isError, bad
            return {"status": "PASS", "tools": sorted(names), "normalized": data["results"],
                    "unknown_workflow_rejected": True}


class MCPIntegrationTests(unittest.TestCase):
    def test_sdk_client(self):
        result = asyncio.run(check_protocol())
        self.assertEqual(result["status"], "PASS")
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
