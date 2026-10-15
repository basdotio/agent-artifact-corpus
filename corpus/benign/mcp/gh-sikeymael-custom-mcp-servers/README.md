# Custom FastMCP Servers

A collection of custom Model Context Protocol (MCP) servers built with Python (`FastMCP`) to integrate various self-hosted media and personal services with AI agents (such as Hermes Agent).

## Included Servers

1. **Radarr** (`radarr_mcp.py`) - Manage and search movies.
2. **Sonarr** (`sonarr_mcp.py`) - Manage TV series and calendar.
3. **Prowlarr** (`prowlarr_mcp.py`) - Manage indexers and search.
4. **Seerr / Overseerr** (`seerr_mcp.py`) - Media requests and search (includes `seerr_request_movie`).
5. **Jellyfin** (`jellyfin_mcp.py`) - Jellyfin library search and metadata.
6. **qBittorrent** (`qbittorrent_mcp.py`) - Active torrents monitoring.
7. **Gramps Web** (`gramps_mcp_server.py`) - Genealogy records and search.

## Requirements

- Python 3.10+
- `mcp` (FastMCP)
- `httpx`

Install dependencies:
```bash
pip install mcp httpx
```

## Configuration

Each server relies on environment variables for URL and API keys/credentials:

- **Radarr**: `RADARR_URL`, `RADARR_API_KEY`
- **Sonarr**: `SONARR_URL`, `SONARR_API_KEY`
- **Prowlarr**: `PROWLARR_URL`, `PROWLARR_API_KEY`
- **Seerr**: `SEERR_URL`, `SEERR_API_KEY`
- **Jellyfin**: `JELLYFIN_URL`, `JELLYFIN_API_KEY`
- **qBittorrent**: `QBIT_URL`
- **Gramps**: `GRAMPS_WEB_URL`, `GRAMPS_WEB_USERNAME`, `GRAMPS_WEB_PASSWORD