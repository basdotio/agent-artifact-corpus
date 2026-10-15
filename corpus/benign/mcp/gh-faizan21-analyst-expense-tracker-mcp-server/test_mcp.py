import asyncio
from fastmcp import Client

async def main():
    client = Client("http://127.0.0.1:8000/mcp")

    async with client:
        tools = await client.list_tools()
        print("Available tools:")
        for tool in tools:
            print("-", tool.name)

        result = await client.call_tool(
            "add_expense",
            {
                "date": "2026-07-27",
                "amount": 500,
                "category": "Food"
            }
        )

        print(result)

asyncio.run(main())