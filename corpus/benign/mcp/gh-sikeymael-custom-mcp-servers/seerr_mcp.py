#!/usr/bin/env python3
import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SeerrMCP")

SEERR_URL = os.environ.get("SEERR_URL", "http://localhost:5055")
SEERR_KEY = os.environ.get("SEERR_API_KEY", "")

def get_headers():
    return {"X-Api-Key": SEERR_KEY}

@mcp.tool()
def seerr_list_requests() -> list:
    """List media requests in Seerr / Overseerr."""
    try:
        res = httpx.get(f"{SEERR_URL}/api/v1/request", headers=get_headers(), timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def seerr_search(query: str) -> list:
    """Search movies or TV shows in Seerr / Overseerr."""
    try:
        res = httpx.get(f"{SEERR_URL}/api/v1/search", headers=get_headers(), params={"query": query}, timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def seerr_get_pending_requests() -> list:
    """Get pending media requests awaiting approval in Seerr / Overseerr."""
    try:
        res = httpx.get(f"{SEERR_URL}/api/v1/request", headers=get_headers(), params={"filter": "pending"}, timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def seerr_request_movie(tmdb_id: int, media_language_profile_id: int = None, quality_profile_id: int = None, server_id: int = None, profile_id: int = None, is_4k: bool = False) -> dict:
    """Request a movie by TMDB ID in Seerr / Overseerr."""
    try:
        body = {
            "mediaType": "movie",
            "mediaId": tmdb_id,
            "is4k": is_4k
        }
        if media_language_profile_id is not None:
            body["languageProfileId"] = media_language_profile_id
        if quality_profile_id is not None:
            body["qualityProfileId"] = quality_profile_id
        if server_id is not None:
            body["serverId"] = server_id
        if profile_id is not None:
            body["profileId"] = profile_id
        res = httpx.post(f"{SEERR_URL}/api/v1/request", headers=get_headers(), json=body, timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
