import asyncio
import json

from typer import Typer

from settings import settings

mcp_typer = Typer(add_completion=False)


# MCP Typer CLI commands
@mcp_typer.command()
def run(
    transport: str = settings.MCP_SERVER_DEFAULT_TRANSPORT,
    port: int | None = settings.MCP_SERVER_DEFAULT_PORT,
):
    """
    Run the MCP server with the specified transport and port.

    --transport: The transport method to use for the MCP server. Options are "stdio" or "streamable-http". Default is "stdio".
    --port: The port number to use for the MCP server when using "streamable-http" transport. Default is 8000.
    """
    from mcp_server import mcp

    if transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport="streamable-http", port=port)


@mcp_typer.command()
def list_tools():
    """
    List all available tools in the MCP server.
    """
    asyncio.run(list_mcp_tools())


async def list_mcp_tools():
    from mcp_server import mcp

    tools = await mcp.list_tools()
    for tool in tools:
        print(f"Tool: {tool.name}")
        print(f"Title: {tool.title}")
        print(f"Description: {tool.description}")
        print(f"Tags: {', '.join(sorted(tool.tags))}")
        print(f"Annotations: {tool.annotations}")
        print(f"Parameters: {json.dumps(tool.parameters, indent=4)}")
        print(f"Output Schema: {json.dumps(tool.output_schema, indent=4)}")
        print("-" * 40)


if __name__ == "__main__":  # pragma: no cover
    mcp_typer()
