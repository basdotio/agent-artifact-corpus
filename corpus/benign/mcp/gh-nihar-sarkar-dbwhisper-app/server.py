from fastmcp import FastMCP
from app.tools import handle_user_query, get_db_metadata


def create_mcp_server() -> FastMCP:
    mcp = FastMCP(name="DBWHISPER - MCP Server")
    mcp.tool()(handle_user_query)
    mcp.tool()(get_db_metadata)
    return mcp
