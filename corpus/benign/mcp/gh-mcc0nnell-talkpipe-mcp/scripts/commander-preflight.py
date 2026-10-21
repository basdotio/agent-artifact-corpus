#!/usr/bin/env python3
"""Verify the signed local Commander MCP surface without Cloudflare or tunnel credentials."""
import asyncio
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REQUIRED_TOOLS = {
    "commander_health",
    "commander_status",
    "commander_talkpipe_run",
    "commander_host_inspect",
    "commander_process_list",
    "commander_git_inspect",
    "commander_file_create",
    "commander_process_probe",
}
REQUIRED_CAPABILITIES = {
    "talkpipe.run", "host.inspect", "process.inspect",
    "git.inspect", "file.create", "process.probe",
}


async def check() -> None:
    root = Path(__file__).resolve().parent.parent
    server = StdioServerParameters(
        command=sys.executable,
        args=["-u", str(root / "windanvil_commander_mcp.py")],
        cwd=str(root),
        env=os.environ.copy(),
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            tools = (await client.list_tools()).tools
            names = {tool.name for tool in tools}
            if names != REQUIRED_TOOLS:
                raise RuntimeError(
                    "tool schema mismatch: missing=" + ",".join(sorted(REQUIRED_TOOLS - names))
                    + " unexpected=" + ",".join(sorted(names - REQUIRED_TOOLS))
                )
            for tool in tools:
                if tool.annotations is None:
                    raise RuntimeError("missing tool annotations: " + tool.name)
                writable = tool.name in {"commander_file_create", "commander_talkpipe_run"}
                if bool(tool.annotations.readOnlyHint) == writable:
                    raise RuntimeError("incorrect readOnlyHint: " + tool.name)

            for tool, inputs in [
                ("commander_health", {}),
                ("commander_status", {}),
                ("commander_host_inspect", {"operation": "system.info", "path": ""}),
                ("commander_process_list", {}),
                ("commander_git_inspect", {"operation": "git.status"}),
            ]:
                response = await client.call_tool(tool, inputs)
                if response.isError:
                    raise RuntimeError("MCP error from " + tool)
                data = response.structuredContent
                if not data:
                    if not response.content:
                        raise RuntimeError("missing MCP tool response: " + tool)
                    data = json.loads(response.content[0].text)
                if "result" in data:
                    data = data["result"]
                if data.get("outcome") != "PASS":
                    raise RuntimeError(tool + " blocked: " + str(data.get("reason", "unknown")))
                if tool == "commander_status":
                    missing = [cap for cap in REQUIRED_CAPABILITIES if cap not in data.get("blade", "")]
                    if missing:
                        raise RuntimeError("signed grants missing: " + ",".join(sorted(missing)))

            print(json.dumps({
                "outcome": "PASS",
                "transport": "local-stdio",
                "tools": len(names),
                "signed_capabilities": len(REQUIRED_CAPABILITIES),
                "executed_checks": 5,
                "cloud_tunnel_connected": False,
                "note": "Local preflight only. Requires an authorized Platform tunnel and ChatGPT connection.",
            }, sort_keys=True))


if __name__ == "__main__":
    try:
        asyncio.run(check())
    except Exception as exc:
        print(json.dumps({
            "outcome": "BLOCKED",
            "reason": str(exc)[:220],
            "cloud_tunnel_connected": False,
        }, sort_keys=True), file=sys.stderr)
        sys.exit(1)
