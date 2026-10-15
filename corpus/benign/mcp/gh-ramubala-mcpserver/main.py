from fastmcp import FastMCP

mcp = FastMCP(name="testserver",
              instructions="Answer the question as truthfully as possible, and if you don't know the answer, say you don't know.",
              icons={"tool": "🔧", "resource": "📁", "prompt": "💬"})

@mcp.tool
def multiply(a: float, b: float) -> float:
    """Multiplies two numbers together."""
    return a * b

@mcp.resource("data://config")
def get_config() -> dict:
    return {"theme": "dark", "version": "1.0"}

@mcp.prompt
def analyze_data(data_points: list[float]) -> str:
    formatted_data = ", ".join(str(point) for point in data_points)
    return f"Please analyze these data points: {formatted_data}"


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=9000)