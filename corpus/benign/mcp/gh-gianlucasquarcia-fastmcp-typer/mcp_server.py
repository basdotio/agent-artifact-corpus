from fastmcp import FastMCP

import mcp_server_prompts
import mcp_server_resources
import mcp_server_tools
from mcp_server_cli import mcp_typer

mcp = FastMCP("My Server")
mcp.mount(mcp_server_tools.mcp)
mcp.mount(mcp_server_resources.mcp)
mcp.mount(mcp_server_prompts.mcp)

if __name__ == "__main__":  # pragma: no cover
    mcp_typer()
