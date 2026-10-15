import os
from typing import Optional

import httpx
from fastmcp import FastMCP

mcp = FastMCP("xgd")

API_ENDPOINT = "https://xgd.io/V1/shorten"


def get_api_key() -> str:
    key = os.environ.get("XGD_API_KEY")
    if not key:
        raise ValueError("XGD_API_KEY environment variable is not set")
    return key


@mcp.tool()
async def shorten_url(
    url: str,
    shortid: Optional[str] = None,
    analytics: Optional[bool] = None,
    filterbots: Optional[bool] = None,
) -> dict:
    """
    Shorten a URL using x.gd API.

    Args:
        url: The URL to shorten (required, must be http(s)://)
        shortid: Custom short ID (6-15 chars, alphanumeric and underscore only)
        analytics: Enable access analytics (default: true)
        filterbots: Enable bot filtering when analytics is enabled (default: false)

    Returns:
        dict with status, shorturl, analytics, filterbots, originalurl
    """
    api_key = get_api_key()

    params = {
        "url": url,
        "key": api_key,
    }

    if shortid is not None:
        params["shortid"] = shortid
    if analytics is not None:
        params["analytics"] = "true" if analytics else "false"
    if filterbots is not None:
        params["filterbots"] = "true" if filterbots else "false"

    async with httpx.AsyncClient() as client:
        response = await client.get(API_ENDPOINT, params=params)
        return response.json()


def main():
    # Use stdio transport without banner for MCP compatibility
    import sys
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
