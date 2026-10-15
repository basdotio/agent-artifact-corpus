# -*- coding: utf-8 -*-
"""
Unsplash MCP Server

An MCP server for fetching photos from Unsplash with proper attribution.
Designed for LLMs building content pages that need properly credited images.
"""

import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Union

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Unsplash API base URL
UNSPLASH_API_BASE = "https://api.unsplash.com"

# Create the MCP server
mcp = FastMCP("Unsplash MCP Server")


@dataclass
class UnsplashPhoto:
    """
    Represents an Unsplash photo with full attribution data.

    The attribution_text and attribution_html fields are ready to use
    directly in content pages without any URL construction needed.
    """
    # Core photo data
    id: str
    description: Optional[str]
    alt_description: Optional[str]

    # Image URLs (multiple sizes: raw, full, regular, small, thumb)
    urls: Dict[str, str]

    # Dimensions
    width: int
    height: int

    # Visual metadata
    color: str  # Dominant hex color for placeholders
    blur_hash: Optional[str]  # BlurHash for progressive loading

    # Attribution (REQUIRED by Unsplash API guidelines)
    photographer_name: str
    photographer_username: str
    photographer_url: str  # Link to photographer's Unsplash profile
    photo_url: str  # Link to photo on Unsplash

    # Ready-to-use attribution strings
    attribution_text: str  # Plain text: "Photo by Name on Unsplash"
    attribution_html: str  # HTML with links for web pages


def _get_access_key() -> str:
    """Get the Unsplash API access key from environment."""
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key:
        raise ValueError(
            "Missing UNSPLASH_ACCESS_KEY environment variable. "
            "Get your key from https://unsplash.com/developers"
        )
    return access_key


def _get_headers() -> Dict[str, str]:
    """Get the headers for Unsplash API requests."""
    return {
        "Accept-Version": "v1",
        "Authorization": f"Client-ID {_get_access_key()}"
    }


def _photo_to_dataclass(photo: dict) -> UnsplashPhoto:
    """Convert an Unsplash API photo response to our UnsplashPhoto dataclass."""
    user = photo["user"]
    photographer_name = user.get("name", user["username"])
    photographer_username = user["username"]
    photographer_url = f"https://unsplash.com/@{photographer_username}?utm_source=mcp_server&utm_medium=referral"
    photo_url = photo["links"]["html"] + "?utm_source=mcp_server&utm_medium=referral"

    # Build ready-to-use attribution strings
    attribution_text = f"Photo by {photographer_name} on Unsplash"
    attribution_html = (
        f'Photo by <a href="{photographer_url}">{photographer_name}</a> '
        f'on <a href="https://unsplash.com/?utm_source=mcp_server&utm_medium=referral">Unsplash</a>'
    )

    return UnsplashPhoto(
        id=photo["id"],
        description=photo.get("description"),
        alt_description=photo.get("alt_description"),
        urls=photo["urls"],
        width=photo["width"],
        height=photo["height"],
        color=photo.get("color", "#000000"),
        blur_hash=photo.get("blur_hash"),
        photographer_name=photographer_name,
        photographer_username=photographer_username,
        photographer_url=photographer_url,
        photo_url=photo_url,
        attribution_text=attribution_text,
        attribution_html=attribution_html,
    )


@mcp.tool()
async def search_photos(
    query: str,
    page: Union[int, str] = 1,
    per_page: Union[int, str] = 10,
    order_by: str = "relevant",
    color: Optional[str] = None,
    orientation: Optional[str] = None,
    content_filter: str = "low"
) -> List[UnsplashPhoto]:
    """
    Search for photos on Unsplash by keyword.

    Use this tool when you need to find photos for a specific topic or theme.
    Each result includes full attribution data that MUST be displayed when
    using the image (required by Unsplash API guidelines).

    Args:
        query: Search keyword(s), e.g. "mountain landscape", "coffee shop interior"
        page: Page number for pagination (default: 1)
        per_page: Number of results per page, 1-30 (default: 10)
        order_by: Sort order - "relevant" (best match) or "latest" (newest first)
        color: Filter by color - black_and_white, black, white, yellow, orange,
               red, purple, magenta, green, teal, blue
        orientation: Filter by orientation - landscape, portrait, squarish
        content_filter: Safety filter - "low" (default) or "high" (stricter)

    Returns:
        List of UnsplashPhoto objects. Each photo includes:
        - urls: Dict with raw, full, regular, small, thumb sizes
        - attribution_text: Plain text credit (e.g. "Photo by John Doe on Unsplash")
        - attribution_html: HTML credit with proper links for web pages

    Example:
        photos = search_photos("sunset beach", per_page=5, orientation="landscape")
        # Use photos[0].urls["regular"] for the image
        # Use photos[0].attribution_html for the credit line
    """
    # Ensure page and per_page are integers
    try:
        page_int = int(page)
    except (ValueError, TypeError):
        page_int = 1

    try:
        per_page_int = int(per_page)
    except (ValueError, TypeError):
        per_page_int = 10

    # Build request parameters
    params = {
        "query": query,
        "page": max(1, page_int),
        "per_page": min(max(1, per_page_int), 30),
        "order_by": order_by,
        "content_filter": content_filter,
    }

    if color:
        params["color"] = color
    if orientation:
        params["orientation"] = orientation

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{UNSPLASH_API_BASE}/search/photos",
                params=params,
                headers=_get_headers(),
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            return [_photo_to_dataclass(photo) for photo in data["results"]]

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise ValueError("Invalid Unsplash API key. Check your UNSPLASH_ACCESS_KEY.")
        elif e.response.status_code == 403:
            raise ValueError("Rate limit exceeded. Unsplash allows 50 requests/hour in demo mode.")
        else:
            raise ValueError(f"Unsplash API error: {e.response.status_code} - {e.response.text}")
    except httpx.TimeoutException:
        raise ValueError("Request timed out. Please try again.")
    except Exception as e:
        raise ValueError(f"Failed to search photos: {str(e)}")


@mcp.tool()
async def get_random_photos(
    query: Optional[str] = None,
    count: Union[int, str] = 1,
    orientation: Optional[str] = None,
    content_filter: str = "low"
) -> List[UnsplashPhoto]:
    """
    Get random photos from Unsplash, optionally filtered by keyword.

    Use this tool when you need variety or don't have a specific image in mind.
    Great for hero images, backgrounds, or when you want to avoid repetitive results.

    Args:
        query: Optional keyword to filter random photos (e.g. "nature", "technology")
        count: Number of random photos to return, 1-30 (default: 1)
        orientation: Filter by orientation - landscape, portrait, squarish
        content_filter: Safety filter - "low" (default) or "high" (stricter)

    Returns:
        List of UnsplashPhoto objects with full attribution data.

    Example:
        # Get 3 random landscape nature photos
        photos = get_random_photos(query="nature", count=3, orientation="landscape")
    """
    # Ensure count is an integer
    try:
        count_int = int(count)
    except (ValueError, TypeError):
        count_int = 1

    count_int = min(max(1, count_int), 30)

    # Build request parameters
    params = {
        "count": count_int,
        "content_filter": content_filter,
    }

    if query:
        params["query"] = query
    if orientation:
        params["orientation"] = orientation

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{UNSPLASH_API_BASE}/photos/random",
                params=params,
                headers=_get_headers(),
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            # API returns a single photo object if count=1, otherwise a list
            if isinstance(data, list):
                return [_photo_to_dataclass(photo) for photo in data]
            else:
                return [_photo_to_dataclass(data)]

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise ValueError("Invalid Unsplash API key. Check your UNSPLASH_ACCESS_KEY.")
        elif e.response.status_code == 403:
            raise ValueError("Rate limit exceeded. Unsplash allows 50 requests/hour in demo mode.")
        else:
            raise ValueError(f"Unsplash API error: {e.response.status_code} - {e.response.text}")
    except httpx.TimeoutException:
        raise ValueError("Request timed out. Please try again.")
    except Exception as e:
        raise ValueError(f"Failed to get random photos: {str(e)}")


@mcp.tool()
async def track_download(photo_id: str) -> str:
    """
    Track a photo download (REQUIRED by Unsplash API guidelines).

    You MUST call this function when a user downloads or saves a photo.
    This is required by Unsplash's API guidelines to properly credit
    photographers and track usage statistics.

    Call this AFTER the user confirms they want to download/use the image,
    not when just displaying search results.

    Args:
        photo_id: The photo ID from a previous search_photos or get_random_photos result

    Returns:
        The download URL for the photo (full resolution)

    Example:
        # User selected a photo to download
        download_url = track_download("abc123xyz")
        # Now serve or redirect to download_url
    """
    if not photo_id or not photo_id.strip():
        raise ValueError("photo_id is required")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{UNSPLASH_API_BASE}/photos/{photo_id}/download",
                headers=_get_headers(),
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            return data.get("url", "")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise ValueError("Invalid Unsplash API key. Check your UNSPLASH_ACCESS_KEY.")
        elif e.response.status_code == 404:
            raise ValueError(f"Photo not found: {photo_id}")
        elif e.response.status_code == 403:
            raise ValueError("Rate limit exceeded. Unsplash allows 50 requests/hour in demo mode.")
        else:
            raise ValueError(f"Unsplash API error: {e.response.status_code} - {e.response.text}")
    except httpx.TimeoutException:
        raise ValueError("Request timed out. Please try again.")
    except Exception as e:
        raise ValueError(f"Failed to track download: {str(e)}")


if __name__ == "__main__":
    mcp.run()
