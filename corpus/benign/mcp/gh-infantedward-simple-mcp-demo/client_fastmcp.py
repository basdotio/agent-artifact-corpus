import asyncio

from fastmcp import Client

from server import mcp


async def main() -> None:
    client = Client(mcp)

    async with client:
        tools = await client.list_tools()
        print("Available tools:")
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")

        result = await client.call_tool("multiply", {"a": 6, "b": 7})
        print("\nTool call:")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
