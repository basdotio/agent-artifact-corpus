from fastmcp import FastMCP

mcp = FastMCP("Demo 🚀")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiplies two numbers together."""
    return a * b

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello, {name}!"

def main():
    print("Hello from fm-mcp!")
    # mcp.run()
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        path="/mcp",
        log_level="debug",
    )

if __name__ == "__main__":
    main()
