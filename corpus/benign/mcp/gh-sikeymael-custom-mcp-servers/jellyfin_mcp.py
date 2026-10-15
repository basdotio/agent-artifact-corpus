#!/usr/bin/env python3
import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("JellyfinMCP")

JELLYFIN_URL = os.environ.get("JELLYFIN_URL", "http://localhost:8096")
JELLYFIN_KEY = os.environ.get("JELLYFIN_API_KEY", "")

def get_headers():
    return {"Authorization": f"MediaBrowser Token=\"{JELLYFIN_KEY}\"", "X-Emby-Token": JELLYFIN_KEY}

@mcp.tool()
def jellyfin_search(term: str) -> list:
    """Search items in Jellyfin library."""
    try:
        res = httpx.get(f"{JELLYFIN_URL}/Items", headers=get_headers(), params={"searchTerm": term, "limit": 20}, timeout=10)
        return res.json().get("Items", [])
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def jellyfin_library_latest() -> list:
    """Get latest added media items in Jellyfin."""
    try:
        res = httpx.get(f"{JELLYFIN_URL}/Items/Latest", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def jellyfin_get_items(parent_id: str = "", include_item_types: str = "") -> list:
    """Get items from Jellyfin with optional parent ID and item types (e.g. Movie, Series)."""
    try:
        params = {}
        if parent_id:
            params["parentId"] = parent_id
        if include_item_types:
            params["IncludeItemTypes"] = include_item_types
        res = httpx.get(f"{JELLYFIN_URL}/Items", headers=get_headers(), params=params, timeout=10)
        return res.json().get("Items", [])
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def jellyfin_get_item_details(item_id: str) -> dict:
    """Get detailed metadata for a specific Jellyfin item ID."""
    try:
        res = httpx.get(f"{JELLYFIN_URL}/Items/{item_id}", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def jellyfin_get_users() -> list:
    """List all Jellyfin users."""
    try:
        res = httpx.get(f"{JELLYFIN_URL}/Users", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def jellyfin_system_info() -> dict:
    """Get Jellyfin server system information."""
    try:
        res = httpx.get(f"{JELLYFIN_URL}/System/Info", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
