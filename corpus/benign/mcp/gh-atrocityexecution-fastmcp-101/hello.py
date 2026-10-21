from fastmcp import FastMCP

mcp = FastMCP("Hello Server")

@mcp.tool
def greet(name: str) -> str:
    """Returns a statement calling somemone
     by their name while saying hello."""
    return f"Hello {name}, welcome to mcp!"

if __name__ == "__main__":
    mcp.run()

