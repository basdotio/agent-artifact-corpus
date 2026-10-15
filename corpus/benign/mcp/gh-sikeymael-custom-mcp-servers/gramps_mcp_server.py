#!/usr/bin/env python3
import os
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("GrampsWeb")

GRAMPS_URL = os.environ.get("GRAMPS_WEB_URL", "http://localhost")
GRAMPS_USERNAME = os.environ.get("GRAMPS_WEB_USERNAME", "")
GRAMPS_PASSWORD = os.environ.get("GRAMPS_WEB_PASSWORD", "")

_token = None

def get_token():
    global _token
    if _token:
        return _token
    try:
        response = httpx.post(f"{GRAMPS_URL}/api/token/", json={
            "username": GRAMPS_USERNAME,
            "password": GRAMPS_PASSWORD
        }, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            _token = data.get("access_token") or data.get("token") or data.get("access")
            return _token
    except Exception as e:
        pass
    return None

def api_get(endpoint: str, params: dict = None):
    token = get_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        # Ensure endpoints do not have double slashes when appended to base
        endpoint = endpoint.lstrip('/')
        res = httpx.get(f"{GRAMPS_URL}/{endpoint}", headers=headers, params=params, timeout=15.0)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def search_people(query: str) -> list:
    """Search individuals in Gramps Web by name or query string."""
    # Gramps Web likely does not support 'search' as a query param on /api/people/
    # Return all for now as a fallback if specific search fails
    data = api_get("/api/people/")
    if isinstance(data, list):
        return [p for p in data if query.lower() in str(p.get("primary_name", "")).lower()]
    return []

@mcp.tool()
def get_person(person_id: str) -> dict:
    """Get detailed information about an individual by ID/handle."""
    return api_get(f"/api/people/{person_id}")

@mcp.tool()
def list_families() -> list:
    """List families in the Gramps database."""
    data = api_get("/api/families/")
    return data if isinstance(data, list) else []

@mcp.tool()
def get_family(family_id: str) -> dict:
    """Get detailed information about a family by ID/handle."""
    return api_get(f"/api/families/{family_id}")

@mcp.tool()
def search_places(query: str) -> list:
    """Search places by name or query."""
    data = api_get("/api/places/")
    if isinstance(data, list):
        return [p for p in data if query.lower() in str(p).lower()]
    return []

@mcp.tool()
def list_bookmark_types() -> list:
    """Get the list of bookmark types/namespaces."""
    data = api_get("/api/bookmarks/")
    return data if isinstance(data, list) else []

@mcp.tool()
def get_bookmarks(namespace: str) -> list:
    """Get list of bookmarks by namespace."""
    data = api_get(f"/api/bookmarks/{namespace}")
    return data if isinstance(data, list) else []

@mcp.tool()
def search_gramps(query: str, type: str = None) -> list:
    """Search objects in Gramps Web (person, family, event, etc.)."""
    params = {"query": query}
    if type:
        params["type"] = type
    data = api_get("/api/search/", params=params)
    return data if isinstance(data, list) else []

if __name__ == "__main__":
    mcp.run()
