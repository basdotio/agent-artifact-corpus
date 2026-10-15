"""
Nova System Agent, exposed as a standard MCP server.
Free, local, no API key. Run standalone or have the orchestrator spawn it.
"""
import subprocess
import shutil
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("nova-system")


@mcp.tool()
def scan_folder(path: str = "~/Downloads") -> dict:
    """Scan a folder and return file count, total size, and file list."""
    full_path = os.path.expanduser(path)
    if not os.path.isdir(full_path):
        return {"error": f"{full_path} is not a valid directory"}
    files = os.listdir(full_path)
    total_size = sum(
        os.path.getsize(os.path.join(full_path, f))
        for f in files if os.path.isfile(os.path.join(full_path, f))
    )
    return {"path": full_path, "file_count": len(files), "total_size_mb": round(total_size / 1e6, 2), "files": files[:50]}


@mcp.tool()
def get_system_info() -> dict:
    """Return CPU, RAM, and disk usage."""
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
    }


@mcp.tool()
def set_volume(level: int) -> str:
    """Set macOS system volume (0-100)."""
    level = max(0, min(100, level))
    subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
    return f"Volume set to {level}"


@mcp.tool()
def take_screenshot(save_path: str = "~/Desktop/nova_screenshot.png") -> str:
    """Take a screenshot and save it."""
    full_path = os.path.expanduser(save_path)
    subprocess.run(["screencapture", full_path])
    return f"Screenshot saved to {full_path}"


@mcp.tool()
def empty_trash() -> str:
    """Empty the macOS trash."""
    subprocess.run(["osascript", "-e", 'tell application "Finder" to empty trash'])
    return "Trash emptied"


if __name__ == "__main__":
    mcp.run()
