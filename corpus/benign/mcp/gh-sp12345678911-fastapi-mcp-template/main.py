from fastmcp import FastMCP
import random

mcp = FastMCP("Demo 🚀",port=9000)

@mcp.tool()
def add(a: int, b: int) -> int:
    """
        Add two numbers
        Args:
            a (int): First number
            b (int): Second number
        Returns:
            int: Sum of a and b
        Example:
            >>> add(1, 2)
            3
    """
    return a + b

@mcp.tool()
def pick_one(options: list[str]) -> str:
    """
        Pick one of options set
        Args:
            options (list[str]): List of options to choose from
    >>> pick_one()
    """
    return random.choice(options)

if __name__ == "__main__":
    mcp.run(transport='sse')