import asyncio
import os

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools.base import ToolResult
from mcp_types import TextContent

from ismalicious_fastmcp.gate import GateClient
from ismalicious_fastmcp.middleware import IsMaliciousMiddleware


async def main() -> None:
    async with GateClient(
        os.environ["ISMALICIOUS_API_KEY"],
        os.environ["ISMALICIOUS_API_SECRET"],
    ) as gate:
        server = FastMCP("Approved documents")
        server.add_middleware(
            IsMaliciousMiddleware(
                gate,
                tools={"fetch_document": "url"},
                allowed_urls={"https://example.com/"},
            )
        )

        @server.tool(output_schema=None, task=False)
        async def fetch_document(url: str) -> ToolResult:
            try:
                async with httpx.AsyncClient(
                    timeout=15,
                    follow_redirects=False,
                    trust_env=False,
                ) as http:
                    async with http.stream("GET", url) as response:
                        if response.status_code != 200:
                            raise ToolError("Document fetch failed")
                        data = bytearray()
                        async for chunk in response.aiter_bytes():
                            data.extend(chunk)
                            if len(data) > 900_000:
                                raise ToolError("Document exceeds the fetch limit")
                text = data.decode("utf-8")
            except (httpx.HTTPError, UnicodeError):
                raise ToolError("Document fetch failed") from None
            return ToolResult(content=[TextContent(type="text", text=text)])

        await server.run_async()


if __name__ == "__main__":
    asyncio.run(main())
