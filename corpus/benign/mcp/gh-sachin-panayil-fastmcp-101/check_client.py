import asyncio

from fastmcp import Client

from weather_server.server import mcp


async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("Tools:", [tool.name for tool in tools])

        result = await client.call_tool(
            "get_weather_forecast", {"location": "Denver", "days_ahead": 2}
        )
        print(result.data)


asyncio.run(main())