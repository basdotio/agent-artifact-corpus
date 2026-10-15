#!/usr/bin/env python3
import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("QbittorrentMCP")

QBIT_URL = os.environ.get("QBIT_URL", "http://localhost:8080")

# Shared session that persists across all calls
_qbit_client = httpx.Client(base_url=QBIT_URL, timeout=10)

@mcp.tool()
def qbit_list_torrents() -> list:
    """List all active torrents in qBittorrent."""
    try:
        res = _qbit_client.get("/api/v2/torrents/info")
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def qbit_transfer_info() -> dict:
    """Get global transfer info (download/upload speed, etc.) in qBittorrent."""
    try:
        res = _qbit_client.get("/api/v2/transfer/info")
        return res.json()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def qbit_pause_torrent(torrent_hash: str) -> str:
    """Pause a torrent by its hash."""
    try:
        res = _qbit_client.post("/api/v2/torrents/pause", data={"hashes": torrent_hash})
        return "Success" if res.status_code == 200 else f"Failed: {res.text}"
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def qbittorrent_resume_torrent(torrent_hash: str) -> str:
    """Resume a torrent by its hash."""
    try:
        res = _qbit_client.post("/api/v2/torrents/resume", data={"hashes": torrent_hash})
        return "Success" if res.status_code == 200 else f"Failed: {res.text}"
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
