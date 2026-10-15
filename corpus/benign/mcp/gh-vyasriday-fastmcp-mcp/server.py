from fastmcp import FastMCP

mcp = FastMCP()


@mcp.tool
def greet(name: str) -> str:
    '''
    greet is a function that takes name as a parameter and returns a greeting
    '''
    return f"Hello {name}"


@mcp.tool
def add_numbers(left: int, right: int) -> int:
    return left + right


if __name__ == "__main__":
    mcp.run()
