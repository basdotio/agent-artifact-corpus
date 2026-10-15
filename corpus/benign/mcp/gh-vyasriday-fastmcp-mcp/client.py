import asyncio

from fastmcp import Client
from fastmcp.exceptions import ToolError
from server import mcp


async def main():
  # Open a connection to this MCP server, call the connected client client, and close the connection when this block finishes.
    async with Client(mcp) as client:
        '''
          1. Client(mcp) creates a FastMCP client configured to communicate with your mcp server object. In this example, communication happens in memory, not through an HTTP connection.

          2. async with enters an asynchronous context manager. FastMCP opens and initializes the connection when the block begins and closes it when the block ends.

          3. as client gives you a variable named client to use inside the block. You could choose another name; client is simply descriptive.
        '''
        print("The connection is open here.")
        # print(dir(client))
        print(await client.list_tools())
        result = await client.call_tool(
            "greet",
            {"name": "Hridayesh"}
        )
        try:
            addition = await client.call_tool(
                "add_numbers",
                {
                    "left": "a",
                    "right": 25
                }
            )
            print(f"sum: {addition.content[0].text}")
        except ToolError as error:
            print(f"Error occured: {error}")
        addition_2 = await client.call_tool(
            "add_numbers",
            {
                "left": 1,
                "right": 25
            }
        )
        print(addition_2.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
