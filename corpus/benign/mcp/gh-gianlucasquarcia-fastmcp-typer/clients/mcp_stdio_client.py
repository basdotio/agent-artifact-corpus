import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.types import ReadResourceResult, TextResourceContents

ROOT = Path(__file__).resolve().parent.parent
SERVER_PATH = ROOT / "mcp_server.py"


def _resource_text(result: ReadResourceResult) -> str:
    content = result.contents[0]
    if not isinstance(content, TextResourceContents):
        raise TypeError(f"Expected text resource, got {type(content).__name__}")
    return content.text


async def main() -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH), "run"],
        cwd=str(ROOT),
    )

    async with Client(server) as client:
        tools_result = await client.list_tools()
        print("Available tools:")
        for tool in tools_result.tools:
            print(f"- {tool.name}: {tool.description}")

        print("\nCalling tool 'time'...")
        result = await client.call_tool("time", {"name": "Alice"})
        print(result.structured_content)

        content_greeting = await client.read_resource("resource://greeting")
        print(_resource_text(content_greeting))

        content_config = await client.read_resource("resource://config")
        print(_resource_text(content_config))

        time_resource = await client.read_resource("resource://time")
        print(_resource_text(time_resource))


if __name__ == "__main__":
    asyncio.run(main())
