import httpx
from fastmcp import FastMCP

mcp = FastMCP("TestServer")


@mcp.tool
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"


@mcp.tool
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@mcp.tool
def cat_fact() -> str:
    """Get a random cat fact."""
    response = httpx.get("https://catfact.ninja/fact")
    response.raise_for_status()
    return response.json()["fact"]


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
