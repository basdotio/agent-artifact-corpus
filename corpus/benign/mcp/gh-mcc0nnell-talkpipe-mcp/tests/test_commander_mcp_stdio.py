"""Exercise the Commander tool facade using a real MCP SDK stdio client."""
import asyncio
import json
import os
import tempfile
from pathlib import Path
import sys
import unittest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def verify():
    root = Path(__file__).resolve().parent.parent
    # Avoid dependence on the host's actual live Blade socket.
    with tempfile.TemporaryDirectory(prefix="commander-mcp-no-blade-") as tmp:
        missing = str(Path(tmp) / "no-blade.sock")
        return await verify_missing_socket(root, missing)


async def verify_missing_socket(root, missing):
    server = StdioServerParameters(
        command=sys.executable,
        args=["-u", str(root / "windanvil_commander_mcp.py")],
        cwd=str(root),
        env={**os.environ, "WINDANVIL_LOCAL_SOCKET": missing},
    )
    async with stdio_client(server) as (reader, writer):
        async with ClientSession(reader, writer) as client:
            await client.initialize()
            items = (await client.list_tools()).tools
            names = {item.name for item in items}
            assert names == {"commander_health", "commander_status", "commander_talkpipe_run", "commander_host_inspect", "commander_process_list", "commander_git_inspect", "commander_file_create", "commander_process_probe"}, names
            for item in items:
                assert item.annotations is not None
                if item.name in {"commander_talkpipe_run", "commander_file_create"}:
                    assert item.annotations.readOnlyHint is False
                else:
                    assert item.annotations.readOnlyHint is True
            for tool, args in [
                ("commander_health", {}),
                ("commander_status", {}),
                ("commander_talkpipe_run", {"pipeline": "normalize", "pipeline_sha256": "a" * 64}),
                ("commander_host_inspect", {"operation":"dir.list", "path":""}),
                ("commander_process_list", {}),
                ("commander_git_inspect", {"operation": "git.status"}),
                ("commander_file_create", {"path": "notes.txt", "content": "hi"}),
                ("commander_process_probe", {"probe": "uptime"}),
            ]:
                result = await client.call_tool(tool, args)
                assert not result.isError, (tool, result)
                data = result.structuredContent
                if not data:
                    assert result.content
                    data = json.loads(result.content[0].text)
                if "result" in data: data = data["result"]
                assert data["outcome"] == "BLOCKED", (tool, data)
            return sorted(names)


class LiveMCPTest(unittest.TestCase):
    def test_stdio_discovery_and_no_blade(self):
        names = asyncio.run(verify())
        print("Commander MCP: PASS", names, "with absent Blade => BLOCKED")


if __name__ == "__main__":
    unittest.main()
