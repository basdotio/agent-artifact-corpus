#!/usr/bin/env python3
import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("RadarrMCP")

RADARR_URL = os.environ.get("RADARR_URL", "http://localhost:7878")
RADARR_KEY = os.environ.get("RADARR_API_KEY", "")

def get_headers():
    return {"X-Api-Key": RADARR_KEY}

@mcp.tool()
def radarr_list_movies() -> list:
    """List all movies managed in Radarr."""
    try:
        res = httpx.get(f"{RADARR_URL}/api/v3/movie", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def radarr_search_movie(term: str) -> list:
    """Search for a new movie to add in Radarr."""
    try:
        res = httpx.get(f"{RADARR_URL}/api/v3/movie/lookup", headers=get_headers(), params={"term": term}, timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def radarr_get_movie_by_id(movie_id: int) -> dict:
    """Get detailed information for a specific Radarr movie ID."""
    try:
        res = httpx.get(f"{RADARR_URL}/api/v3/movie/{movie_id}", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def radarr_get_queue() -> list:
    """Get current download queue in Radarr."""
    try:
        res = httpx.get(f"{RADARR_URL}/api/v3/queue", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def radarr_list_commands() -> list:
    """List running or completed commands in Radarr."""
    try:
        res = httpx.get(f"{RADARR_URL}/api/v3/command", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
