"""
Reddit MCP Server

A Model Context Protocol server for browsing Reddit directly from Claude Desktop.
Supports both anonymous (public) and authenticated access.
"""

import os
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP
from reddit.api import RedditAPI
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# Configuration
# ============================================================================


def get_env_or_none(key: str) -> Optional[str]:
    """
    Get environment variable value, returning None if empty or unsubstituted.

    MCP bundle user_config placeholders like ${user_config.KEY} are passed
    as literal strings when the user hasn't configured them. This function
    detects these cases and returns None instead.

    Args:
        key: Environment variable name

    Returns:
        The value if set and valid, None otherwise
    """
    value = os.environ.get(key, "")
    if not value or value.startswith("${"):
        return None
    return value


def init_reddit_client() -> RedditAPI:
    """
    Initialize Reddit API client with optional OAuth credentials.

    Credentials are read from environment variables:
    - REDDIT_CLIENT_ID: Reddit API client ID
    - REDDIT_CLIENT_SECRET: Reddit API client secret

    If credentials are not provided, the client operates in anonymous mode
    with lower rate limits but no authentication required.

    Returns:
        Configured RedditAPI instance
    """
    client_id = get_env_or_none("REDDIT_CLIENT_ID")
    client_secret = get_env_or_none("REDDIT_CLIENT_SECRET")

    client = RedditAPI(client_id=client_id, client_secret=client_secret)

    # Log authentication mode for debugging
    if client.use_oauth:
        print("Reddit MCP: Using OAuth authentication", file=sys.stderr)
    else:
        print("Reddit MCP: Using anonymous mode (no credentials)", file=sys.stderr)

    return client


# ============================================================================
# Server Initialization
# ============================================================================

# Check if we should serve over HTTPS/SSE (for remote access)
SERVE_SSE = os.environ.get("SERVE_HTTPS", "").lower() == "true"

if SERVE_SSE:
    mcp = FastMCP("reddit-mcp", host="0.0.0.0", port=8000)
else:
    mcp = FastMCP("reddit-mcp")

reddit = init_reddit_client()


# ============================================================================
# MCP Tools
# ============================================================================


@mcp.tool()
def browse_subreddit(
    subreddit: str,
    sort: str = "hot",
    limit: int = 25,
    after: Optional[str] = None,
    time_filter: Optional[str] = None,
):
    """Browse a subreddit.

    Args:
        subreddit: Subreddit to browse (e.g., 'python', 'programming')
        sort: Sort order - 'hot', 'new', 'top', 'rising' (default: hot)
        limit: Number of posts to return, max 100 (default: 25)
        after: Cursor for pagination from previous response (default: None)
        time_filter: Time filter for 'top' sort - 'hour', 'day', 'week', 'month', 'year', 'all' (default: None)
    """
    return reddit.browse_subreddit(subreddit, sort, limit, after, time_filter)


@mcp.tool()
def search_reddit(
    query: str,
    subreddit: Optional[str] = None,
    sort: str = "relevance",
    limit: int = 25,
):
    """Search Reddit for posts.

    Args:
        query: Search query string
        subreddit: Limit search to specific subreddit (default: search all of Reddit)
        sort: Sort order - 'relevance', 'hot', 'top', 'new', 'comments' (default: relevance)
        limit: Number of posts to return, max 100 (default: 25)
    """
    return reddit.search_reddit(query, subreddit, sort, limit)


@mcp.tool()
def get_post_details(post_id: str, max_comments: int = 100):
    """Get full details of a Reddit post including comments.

    Args:
        post_id: The Reddit post ID (e.g., '1abc23d')
        max_comments: Maximum number of comments to return (default: 100)
    """
    return reddit.get_post_details(post_id, max_comments)


@mcp.tool()
def user_analysis(username: str, limit: int = 50):
    """Analyze a Reddit user's activity and statistics.

    Args:
        username: Reddit username to analyze (without u/ prefix)
        limit: Number of recent posts/comments to analyze (default: 50)
    """
    return reddit.user_analysis(username, limit)


# ============================================================================
# Entry Point
# ============================================================================


def main():
    """Run the MCP server."""
    if SERVE_SSE:
        print("Reddit MCP: Starting SSE server on 0.0.0.0:8000", file=sys.stderr)
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
