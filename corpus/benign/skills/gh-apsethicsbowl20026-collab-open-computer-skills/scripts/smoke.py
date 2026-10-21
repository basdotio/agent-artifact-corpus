"""MCP smoke test — no mouse moves, no clicks. Lists tools + echo via bash_exec.

Usage:
  python scripts/smoke.py --server "C:/path/to/backend/mcp_server.py"
"""
import argparse, asyncio, sys
from pathlib import Path

async def run(server: str):
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession
    params = StdioServerParameters(command=sys.executable, args=[server])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            names = sorted(t.name for t in tools.tools)
            print("TOOLS:", ", ".join(names))
            assert {"screenshot", "computer_action", "desktop_snapshot", "desktop_act", "bash_exec"} <= set(names), "missing tools"
            res = await s.call_tool("bash_exec", {"command": "echo mcp-ok"})
            txt = res.content[0].text if res.content else ""
            print("CALL-OK:", txt.strip()[:200])
            assert "mcp-ok" in txt, "echo failed"
            print("SMOKE-PASS")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    a = ap.parse_args()
    if not Path(a.server).exists():
        sys.exit(f"server not found: {a.server}")
    asyncio.run(run(str(Path(a.server).resolve())))

if __name__ == "__main__":
    main()
