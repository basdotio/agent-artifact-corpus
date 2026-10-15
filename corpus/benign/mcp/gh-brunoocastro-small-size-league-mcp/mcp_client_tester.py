import asyncio

# Verify if the server is running at localhost:8888
from fastmcp import Client

from mcp_server import mcp

# All the content here is based on the [oficial documentation of the FastMCP project](https://gofastmcp.com/clients/client).
# The goal of this file is to help us to test the FastMCP server using the client.
# 1. We will test the python file (in-memory) server ([mcp.py](./mcp.py))
# 2. We will test the FastMCP server using Server Side Events (SSE) (running `mcp.py` with `transport="sse"`)

# 1. Test the python file (in-memory) server

in_memory_client = Client(mcp)


async def test_in_memory_server():
    print("-" * 6, "STARTING IN-MEMORY SERVER TEST", "-" * 6)
    async with in_memory_client:
        available_tools = await in_memory_client.list_tools()
        print(
            f"[IN-MEMORY SERVER] available_tools (length: {len(available_tools)}): \n{available_tools}\n\n"
        )
        available_resources = await in_memory_client.list_resources()
        print(
            f"[IN-MEMORY SERVER] available_resources (length: {len(available_resources)}): \n{available_resources}\n\n"
        )
        # Test the full-text tool
        full_text_tool = await in_memory_client.read_resource("full-text://website")
        print(
            f"[IN-MEMORY SERVER] full_text_tool preview (length: {len(full_text_tool)}): {full_text_tool[0].text[:100]}\n\n"
        )
        # Test the full-text tool
        full_rules_tool = await in_memory_client.read_resource("full-text://rules")
        print(
            f"[IN-MEMORY SERVER] full_rules_tool preview (length: {len(full_rules_tool)}): {full_rules_tool[0].text[:100]}\n\n"
        )
        full_repository_tool = await in_memory_client.read_resource(
            "full-text://repository"
        )
        print(
            f"[IN-MEMORY SERVER] full_repository_tool preview (length: {len(full_repository_tool)}): {full_repository_tool[0].text[:100]}\n\n"
        )
    print("-" * 6, "END OF IN-MEMORY SERVER TEST", "-" * 6)


asyncio.run(test_in_memory_server())

# 2. Test the FastMCP server using Server Side Events (SSE)
print("-" * 6, "STARTING SSE SERVER", "-" * 6)

print(
    "[SSE SERVER] You must run the server first. Run `python mcp_server.py` to start the server."
)
sse_client = Client("http://localhost:8888/sse")


async def test_sse_server():
    print("-" * 6, "STARTING SSE SERVER TEST", "-" * 6)
    async with sse_client:
        available_tools = await sse_client.list_tools()
        print(
            f"[SSE SERVER] available_tools (length: {len(available_tools)}): \n{available_tools}\n\n"
        )
        available_resources = await sse_client.list_resources()
        print(
            f"[SSE SERVER] available_resources (length: {len(available_resources)}): \n{available_resources}\n\n"
        )
    print("-" * 6, "END OF SSE SERVER TEST", "-" * 6)


asyncio.run(test_sse_server())
