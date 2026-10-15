"""Read-only tool server.

The optional SDK transport implements protocol lifecycle and negotiation. ``handle``
and ``serve`` are the dependency-free compatibility adapter used by offline demos.
Install ``byte-agent-platform[mcp]`` and use ``--sdk`` for host integration.
"""
import argparse
import asyncio
import json
import sys

PROTOCOL = "2025-11-25"


def handle(request, tools):
    identity = request.get("id")
    if "id" not in request:
        return None
    response = {"jsonrpc": "2.0", "id": identity}
    method = request.get("method")
    params = request.get("params", {})
    if request.get("jsonrpc") != "2.0" or not isinstance(params, dict):
        response["error"] = {"code": -32600, "message": "Invalid request"}
    elif method == "initialize":
        response["result"] = {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                              "serverInfo": {"name": "byte-agent-tools", "version": "0.1.0"}}
    elif method == "ping":
        response["result"] = {}
    elif method == "tools/list":
        response["result"] = {"tools": [t.spec() for t in tools.values()]}
    elif method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or name not in tools:
            response["error"] = {"code": -32602, "message": "Unknown tool"}
        else:
            try:
                result = tools[name].call(params.get("arguments", {}))
                response["result"] = {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                                      "structuredContent": result, "isError": False}
            except Exception as exc:
                response["result"] = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    else:
        response["error"] = {"code": -32601, "message": "Method not found"}
    return response


def serve(tools):
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("request must be object")
            response = handle(request, tools)
        except (ValueError, TypeError):
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Invalid JSON request"}}
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


async def serve_sdk_async(tools):
    """Serve a registry over stdio using the official MCP Python SDK 1.x."""
    try:
        import mcp.types as types
        from mcp.server.lowlevel import Server
        from mcp.server.stdio import stdio_server
    except ImportError as exc:
        raise RuntimeError("SDK transport requires: pip install 'byte-agent-platform[mcp]'") from exc
    server = Server("byte-agent-tools", version="0.2.0")

    @server.list_tools()
    async def list_tools():
        return [types.Tool(**tool.spec(), annotations=types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True,
            openWorldHint=False)) for tool in tools.values()]

    @server.call_tool()
    async def call_tool(name, arguments):
        # Execute on this event-loop thread: Knowledge owns a SQLite connection.
        if name not in tools:
            raise ValueError("Unknown tool")
        result = tools[name].call(arguments or {})
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
            structuredContent=result, isError=False)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def serve_sdk(tools):
    asyncio.run(serve_sdk_async(tools))


def main():
    from pathlib import Path
    from .knowledge import Knowledge
    from .tools import registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--sdk", action="store_true")
    args = parser.parse_args()
    knowledge = Knowledge(args.data / "knowledge.sqlite")
    try:
        tools = registry(knowledge, args.data / "metrics.sqlite")
        (serve_sdk if args.sdk else serve)(tools)
    finally:
        knowledge.db.close()


if __name__ == "__main__":
    main()
