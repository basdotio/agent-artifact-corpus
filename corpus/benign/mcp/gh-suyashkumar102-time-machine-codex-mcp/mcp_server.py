import asyncio
import requests

from modelcontextprotocol.server import Server
from modelcontextprotocol.server.stdio import stdio_server
from modelcontextprotocol.types import TextContent

server = Server(
    name="codex-refactor-mcp",
    version="1.0.0",
)

def call_backend(path, body):
    url = f"http://localhost:4000{path}"
    res = requests.post(url, json=body)
    return res.json()

@server.call_tool()
async def analyze_code(tool_name: str, args: dict):
    code = args.get("code")
    filename = args.get("filename")
    resp = call_backend("/analyze", {"code": code, "filename": filename})
    return [TextContent(type="text", text=str(resp))]

@server.call_tool()
async def suggest_refactors(tool_name: str, args: dict):
    code = args.get("code")
    filename = args.get("filename")
    resp = call_backend("/suggest", {"code": code, "filename": filename})
    return [TextContent(type="text", text=str(resp))]

async def main():
    print("🔥 Codex Refactor MCP running...", flush=True)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )

if __name__ == "__main__":
    asyncio.run(main())
