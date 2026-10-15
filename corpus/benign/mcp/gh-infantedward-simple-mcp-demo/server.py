import argparse

from fastmcp import FastMCP

from math_tools import add, divide, multiply, subtract


mcp = FastMCP("Math Demo MCP Server")
mcp.add_tool(add)
mcp.add_tool(subtract)
mcp.add_tool(multiply)
mcp.add_tool(divide)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the math MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="Transport to use.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port.")
    args = parser.parse_args()

    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
        return

    mcp.run()


if __name__ == "__main__":
    main()
