# GitHub Profile MCP Server

An MCP (Model Context Protocol) server that exposes your public GitHub profile and repository data as structured tools, without needing to browse the web.

## What it does

Query your GitHub profile, repositories, stars, languages, and activity directly from any MCP-compatible client:

```
You: "What languages do I use most across my repos?"
[queries your public repos, analyzes language distribution, returns breakdown]

You: "Summarize my omkar-ramesh profile repo for me"
[fetches detailed repo info, returns description, stats, topics]
```

## Features

- **`get_profile`** — Fetch your public GitHub profile (name, bio, location, followers, repo count)
- **`list_repos`** — List your repositories sorted by stars/forks/updates (up to 30)
- **`get_repo_details`** — Get full details on a specific repo (size, issues, topics, language)
- **`get_languages`** — Language breakdown for any repository (% Python, JavaScript, etc)

All endpoints use GitHub's public API — **no authentication required**.

## Install

### 1. Clone and install dependencies

```bash
git clone https://github.com/omkar-ramesh/github-mcp-server-.git
cd github-mcp-server
pip install -e .
```

Or if using uv:
```bash
uv pip install -e .
```

### 2. Configure in Claude

Add this to Claude's MCP configuration file (or via `claude` CLI):

**Claude Desktop (Mac/Windows):**
Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "github-mcp-server": {
      "command": "python",
      "args": ["/path/to/github-mcp-server/github_mcp_server.py"]
    }
  }
}
```

Replace `/path/to/` with the actual path to the repo on your machine.

**Claude CLI:**
```bash
claude mcp add github-mcp-server python /path/to/github_mcp_server.py
```

## Usage

Once configured, ask anything about your GitHub:

```
"What's my most popular repo?"
"How many followers do I have?"
"Show me all repositories written in Python"
"What topics do I tag my projects with?"
"When did I last update my profile?"
```

The MCP server fetches real data from GitHub and returns it directly, no browsing required.

## Configuration

Edit the top of `github_mcp_server.py` to change the default username:

```python
DEFAULT_USERNAME = "omkar-ramesh"  # Change to your GitHub username
```

Or pass a different username when calling the tools from Claude.

## API Reference

### `get_profile(username)`
Fetch public profile information.

**Returns:**
- name, login, bio, location, company
- followers, following, public repos
- GitHub URL, created/updated dates

### `list_repos(username, sort, direction)`
List repositories.

**Args:**
- `sort`: "updated" (default), "stars", "forks", "full_name"
- `direction`: "desc" (default) or "asc"

**Returns:**
- List of up to 30 repos with name, URL, description, language, stars, forks, creation/update dates

### `get_repo_details(username, repo_name)`
Get detailed info on one repository.

**Args:**
- `repo_name`: Repository name (required)

**Returns:**
- Full repo metadata: language, stars, forks, issues, topics, size, is_archived, etc.

### `get_languages(username, repo_name)`
Language breakdown for a repository.

**Args:**
- `repo_name`: Repository name (required)

**Returns:**
- Percentage breakdown of languages (e.g., Python 45%, JavaScript 30%, etc.)

## Limitations

- Uses GitHub's public API (no private repos or data)
- Rate-limited to 60 requests/hour per IP (GitHub's unauthenticated limit)
- For higher limits, add a personal access token to the server (not required for public data)

## Why this matters

This MCP server demonstrates:
- Understanding of the Model Context Protocol (hot skill in 2026)
- Integration between AI assistants and external data sources
- Clean tool design and error handling
- Real, shipping-ready code

## License

MIT

---

Built with the [MCP SDK](https://modelcontextprotocol.io).
