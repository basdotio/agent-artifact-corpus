"""Small real MCP server for the portable example benchmark."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ToolBench calculator")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Return a + b."""
    return a + b


@mcp.tool()
def divide(numerator: float, denominator: float) -> float:
    """Return numerator / denominator. A zero denominator is an error."""
    return numerator / denominator


if __name__ == "__main__":
    mcp.run(transport="stdio")
