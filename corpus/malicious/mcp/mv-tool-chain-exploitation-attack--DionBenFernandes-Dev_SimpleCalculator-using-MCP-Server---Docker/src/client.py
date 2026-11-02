import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

"""
Make sure:
1. The server is running before running this script.
2. The server is configured to use SSE transport.
3. The server is listening on port 8050.

To run the server:
uv run server.py
"""


async def main():
    # Connect to the server using SSE
    async with sse_client("http://localhost:8050/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tool_list = []
            tools_result = await session.list_tools()
            print("Available tools:")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description}")
                tool_list.append(tool.name)

            # choose tool
            while True:
                user_tool = str(input("\nEnter the tool you want to use: "))
                if user_tool in tool_list:
                    # Call our calculator tool
                    a = int(input("\nEnter 1st Number: "))
                    b = int(input("Enter 2nd Number: "))
                    result = await session.call_tool(
                        f"{user_tool}", arguments={"a": a, "b": b}
                    )
                    print(
                        f"\nResult:: {a} {result.content[1].text} {b} = {result.content[0].text}"
                    )
                    break
                else:
                    raise ValueError("Unknown tool:", user_tool)


if __name__ == "__main__":
    asyncio.run(main())
