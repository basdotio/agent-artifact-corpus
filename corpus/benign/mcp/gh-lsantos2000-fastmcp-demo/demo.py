from fastmcp import FastMCP
from tools.math_tools import add, multiply, calculate
from tools.text_tools import greet

# Create your MCP server
mcp = FastMCP("Demo ")

# Register math tools
mcp.tool()(add)
mcp.tool()(multiply)
mcp.tool()(calculate)

# Register text tools
mcp.tool()(greet)

if __name__ == "__main__":
    mcp.run()
