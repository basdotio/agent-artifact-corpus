"""The same three tools as server_v2.py, written for the mcp 1.x SDK (FastMCP)."""

from mcp.server.fastmcp import FastMCP

server = FastMCP("demo-server")


@server.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@server.tool()
def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"


@server.tool()
def boom() -> str:
    """Always fails, with a message that explains why."""
    raise ValueError("kaboom: the upstream API returned 503")


if __name__ == "__main__":
    server.run()
