import asyncio
import json
import tiktoken

from fastmcp import Client


async def benchmark():

    client = Client("http://localhost:8000/mcp")

    async with client:

        tools = await client.list_tools()

        # Only measure CRUD tools
        print("\nALL DISCOVERED TOOLS:")
        for tool in tools:
            print(f"  {tool.name}")

        print("\n" + "=" * 70)
        print("MCP CRUD TOOL BENCHMARK")
        print("=" * 70)

        print(f"\nCRUD tools: {len(tools)}")

        # Convert schemas into JSON
        serialized_tools = []

        for tool in tools:

            tool_data = {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
            }

            serialized_tools.append(tool_data)

        json_data = json.dumps(
            serialized_tools,
            indent=2
        )

        # Approximate token count using cl100k_base
        encoding = tiktoken.get_encoding("cl100k_base")
        token_count = len(encoding.encode(json_data))

        print(f"Serialized schema characters: {len(json_data):,}")
        print(f"Estimated tokens: {token_count:,}")

        print("\nIndividual tools:")

        for tool in tools:

            data = {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
            }

            serialized = json.dumps(data)

            tokens = len(
                encoding.encode(serialized)
            )

            print(
                f"  {tool.name:<22} "
                f"{len(serialized):>5} chars "
                f"{tokens:>4} tokens"
            )

        print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(benchmark())