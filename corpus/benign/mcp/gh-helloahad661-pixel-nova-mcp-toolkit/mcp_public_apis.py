"""MCP server wrapping free public-apis - no key needed. Uses public-apis list as source."""
try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("public-apis")
except ImportError:
    try:
        from mcp.server.mcpserver import MCPServer
        mcp = MCPServer("public-apis")
    except ImportError:
        # Fallback for mcp 2.x - try new location
        from mcp.server import Server as MCPServer
        mcp = MCPServer("public-apis")

import requests

@mcp.tool()
def cat_fact() -> dict:
    """Get a random cat fact - No auth, CORS yes - from public-apis"""
    r = requests.get("https://catfact.ninja/fact", timeout=5)
    return r.json()

@mcp.tool()
def dog_image() -> dict:
    """Get random dog image - No auth"""
    r = requests.get("https://dog.ceo/api/breeds/image/random", timeout=5)
    return r.json()

@mcp.tool()
def studio_ghibli_films() -> dict:
    """List Studio Ghibli films - No auth"""
    r = requests.get("https://ghibliapi.vercel.app/films", timeout=5)
    data = r.json()
    return {"count": len(data), "titles": [f["title"] for f in data[:5]]}

@mcp.tool()
def anime_info(anime_id: int = 1) -> dict:
    """Get anime info from Jikan (MyAnimeList) - No auth - e.g. anime_id 1 = Cowboy Bebop"""
    r = requests.get(f"https://api.jikan.moe/v4/anime/{anime_id}", timeout=5)
    j = r.json()
    return {"title": j["data"]["title"], "synopsis": j["data"]["synopsis"][:200]}

@mcp.tool()
def coingecko_ping() -> dict:
    """Ping CoinGecko crypto API - No auth"""
    r = requests.get("https://api.coingecko.com/api/v3/ping", timeout=5)
    return r.json()

if __name__ == "__main__":
    mcp.run()
