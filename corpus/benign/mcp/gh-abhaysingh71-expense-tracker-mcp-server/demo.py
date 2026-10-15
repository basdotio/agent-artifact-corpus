import random
from fastmcp import FastMCP

# Create a FastMCP instance
mcp = FastMCP(name = "Demo Server")

@mcp.tool
def roll_dice(n_dice:int =1) -> list[int]:
    """Roll n six-sided dice and return the results."""
    return [random.randint(1, 6) for _ in range(n_dice)]

@mcp.tool
def add_number(a:float, b:float) -> float:
    """Add two numbers and return the result."""
    return a + b

if __name__ == "__main__":
    # Start the FastMCP server
    mcp.run()
    


# run mcp inspector
# uv run fastmcp dev main.py

# run mcp server
# uv run fastmcp run main.py

# add mcp to claude desktop
# uv run fastmcp install claude-desktop main.py