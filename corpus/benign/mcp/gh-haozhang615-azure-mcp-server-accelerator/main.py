import os
from mcp.server.fastmcp import FastMCP

# Get port from environment variable, default to 3000
port = int(os.getenv("PORT", 3000))

mcp = FastMCP(host="0.0.0.0", port=port, stateless_http=True)

@mcp.tool()
def create_slogan(word: str) -> str:
    """Create a slogan for Microsoft with the given word."""
    return f"Microsoft = {word}"

if __name__ == "__main__":
    print(f"Starting MCP server on port {port}")
    print(f"MCP endpoint available at: http://localhost:{port}/mcp")
    mcp.run(transport="streamable-http")
