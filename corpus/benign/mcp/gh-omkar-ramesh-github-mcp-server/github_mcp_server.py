#!/usr/bin/env python3
"""
GitHub Profile MCP Server
--------------------------
Exposes your GitHub profile and repository data to Claude via the Model Context Protocol.

This server allows Claude to query your public GitHub profile, repositories,
contributions, and activity data without needing to browse the web.

Usage:
    python github_mcp_server.py

Then configure in Claude's MCP settings:
    {
      "github-mcp-server": {
        "command": "python",
        "args": ["/path/to/github_mcp_server.py"]
      }
    }
"""

import requests
import json
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent, ToolResult

# Initialize the MCP server
server = Server("github-profile-server")

# Configuration
GITHUB_API = "https://api.github.com"
DEFAULT_USERNAME = "omkar-ramesh"  # Change to your username


def fetch_github_data(endpoint: str, username: str = DEFAULT_USERNAME) -> dict[str, Any]:
    """Fetch data from GitHub API (public endpoints, no auth needed)."""
    try:
        url = f"{GITHUB_API}/users/{username}/{endpoint}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}


@server.call_tool()
def get_profile(username: str = DEFAULT_USERNAME) -> ToolResult:
    """
    Fetch public GitHub profile information.

    Returns: name, bio, location, company, followers, public repos, and more.
    """
    data = fetch_github_data("", username)

    if "error" in data:
        return ToolResult(
            content=[TextContent(type="text", text=f"Error: {data['error']}")],
            is_error=True,
        )

    profile = {
        "name": data.get("name"),
        "login": data.get("login"),
        "bio": data.get("bio"),
        "location": data.get("location"),
        "company": data.get("company"),
        "blog": data.get("blog"),
        "twitter": data.get("twitter_username"),
        "followers": data.get("followers"),
        "following": data.get("following"),
        "public_repos": data.get("public_repos"),
        "public_gists": data.get("public_gists"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "github_url": data.get("html_url"),
    }

    return ToolResult(
        content=[TextContent(type="text", text=json.dumps(profile, indent=2))],
    )


@server.call_tool()
def list_repos(
    username: str = DEFAULT_USERNAME,
    sort: str = "updated",
    direction: str = "desc",
) -> ToolResult:
    """
    List repositories for a user.

    Args:
        username: GitHub username
        sort: "updated", "stars", "forks", "full_name"
        direction: "asc" or "desc"

    Returns: List of repositories with stars, forks, language, and description.
    """
    data = fetch_github_data(f"repos?sort={sort}&direction={direction}&per_page=30", username)

    if isinstance(data, dict) and "error" in data:
        return ToolResult(
            content=[TextContent(type="text", text=f"Error: {data['error']}")],
            is_error=True,
        )

    repos = []
    for repo in data if isinstance(data, list) else []:
        repos.append({
            "name": repo.get("name"),
            "url": repo.get("html_url"),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count"),
            "forks": repo.get("forks_count"),
            "is_fork": repo.get("fork"),
            "created_at": repo.get("created_at"),
            "updated_at": repo.get("updated_at"),
        })

    return ToolResult(
        content=[TextContent(type="text", text=json.dumps(repos, indent=2))],
    )


@server.call_tool()
def get_repo_details(
    username: str = DEFAULT_USERNAME,
    repo_name: str = None,
) -> ToolResult:
    """
    Get detailed information about a specific repository.

    Args:
        username: GitHub username
        repo_name: Repository name

    Returns: Detailed repo info including topics, size, open issues, and more.
    """
    if not repo_name:
        return ToolResult(
            content=[TextContent(type="text", text="Error: repo_name is required")],
            is_error=True,
        )

    data = fetch_github_data(f"repos/{repo_name}", username)

    if "error" in data:
        return ToolResult(
            content=[TextContent(type="text", text=f"Error: {data['error']}")],
            is_error=True,
        )

    details = {
        "name": data.get("name"),
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "url": data.get("html_url"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "watchers": data.get("watchers_count"),
        "open_issues": data.get("open_issues_count"),
        "size_kb": data.get("size"),
        "topics": data.get("topics", []),
        "is_fork": data.get("fork"),
        "is_archived": data.get("archived"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "pushed_at": data.get("pushed_at"),
    }

    return ToolResult(
        content=[TextContent(type="text", text=json.dumps(details, indent=2))],
    )


@server.call_tool()
def get_languages(
    username: str = DEFAULT_USERNAME,
    repo_name: str = None,
) -> ToolResult:
    """
    Get language breakdown for a repository (what % is Python, JavaScript, etc).

    Args:
        username: GitHub username
        repo_name: Repository name (required)

    Returns: Dictionary of languages and their byte counts.
    """
    if not repo_name:
        return ToolResult(
            content=[TextContent(type="text", text="Error: repo_name is required")],
            is_error=True,
        )

    data = fetch_github_data(f"repos/{repo_name}/languages", username)

    if "error" in data:
        return ToolResult(
            content=[TextContent(type="text", text=f"Error: {data['error']}")],
            is_error=True,
        )

    total_bytes = sum(data.values()) if data else 1
    percentages = {
        lang: f"{(bytes / total_bytes * 100):.1f}%"
        for lang, bytes in data.items()
    }

    return ToolResult(
        content=[TextContent(type="text", text=json.dumps(percentages, indent=2))],
    )


if __name__ == "__main__":
    server.run()
