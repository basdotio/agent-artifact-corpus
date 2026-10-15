#!/usr/bin/env python3
import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ProwlarrMCP")

PROWLARR_URL = os.environ.get("PROWLARR_URL", "http://localhost:9696")
PROWLARR_KEY = os.environ.get("PROWLARR_API_KEY", "")

def get_headers():
    return {"X-Api-Key": PROWLARR_KEY}

@mcp.tool()
def prowlarr_list_indexers() -> list:
    """List all configured indexers in Prowlarr."""
    try:
        res = httpx.get(f"{PROWLARR_URL}/api/v1/indexer", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def prowlarr_search_indexers(query: str, indexer_ids: str = "") -> list:
    """Search across indexers in Prowlarr."""
    try:
        params = {"query": query}
        if indexer_ids:
            params["indexerIds"] = indexer_ids
        res = httpx.get(f"{PROWLARR_URL}/api/v1/search", headers=get_headers(), params=params, timeout=15)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def prowlarr_list_applications() -> list:
    """List connected applications in Prowlarr (Sonarr, Radarr, etc.)."""
    try:
        res = httpx.get(f"{PROWLARR_URL}/api/v1/application", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def prowlarr_list_history() -> list:
    """List search / grab history in Prowlarr."""
    try:
        res = httpx.get(f"{PROWLARR_URL}/api/v1/history", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
