#!/usr/bin/env python3
import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SonarrMCP")

SONARR_URL = os.environ.get("SONARR_URL", "http://localhost:8989")
SONARR_KEY = os.environ.get("SONARR_API_KEY", "")

def get_headers():
    return {"X-Api-Key": SONARR_KEY}

@mcp.tool()
def sonarr_list_series() -> list:
    """List all TV series managed in Sonarr."""
    try:
        res = httpx.get(f"{SONARR_URL}/api/v3/series", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def sonarr_search_series(term: str) -> list:
    """Search for a new TV series to add in Sonarr."""
    try:
        res = httpx.get(f"{SONARR_URL}/api/v3/series/lookup", headers=get_headers(), params={"term": term}, timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def sonarr_get_series_by_id(series_id: int) -> dict:
    """Get detailed information for a specific Sonarr series ID."""
    try:
        res = httpx.get(f"{SONARR_URL}/api/v3/series/{series_id}", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def sonarr_get_calendar(start_date: str = "", end_date: str = "") -> list:
    """Get upcoming TV episodes calendar from Sonarr (YYYY-MM-DD format)."""
    try:
        params = {}
        if start_date:
            params["start"] = start_date
        if end_date:
            params["end"] = end_date
        res = httpx.get(f"{SONARR_URL}/api/v3/calendar", headers=get_headers(), params=params, timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def sonarr_get_queue() -> list:
    """Get current download queue in Sonarr."""
    try:
        res = httpx.get(f"{SONARR_URL}/api/v3/queue", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def sonarr_list_commands() -> list:
    """List running or completed commands in Sonarr."""
    try:
        res = httpx.get(f"{SONARR_URL}/api/v3/command", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
