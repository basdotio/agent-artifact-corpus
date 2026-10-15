"""MeshVault Eufy camera MCP server (read-first: snapshots + status, no PTZ)."""
from __future__ import annotations

import json
import math
import subprocess
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from fastmcp import FastMCP

MEDIA_MTX_RTSP = "rtsp://127.0.0.1:8554"
MEDIA_MTX_API = "http://127.0.0.1:9997"
SNAP_DIR = Path.home() / "meshvault" / "camera" / "snapshots"
REC_DIR = Path.home() / "meshvault" / "camera" / "recordings"
KNOWN_CAMS = ("eufy_cam1", "eufy_cam2", "eufy_cam3", "eufy_cam4")

mcp = FastMCP("eufy-cam")


def _api_paths() -> list[dict]:
    with urllib.request.urlopen(f"{MEDIA_MTX_API}/v3/paths/list", timeout=5) as resp:
        return json.loads(resp.read().decode()).get("items", [])


@mcp.tool
def list_cameras() -> list[dict]:
    """List known Eufy cameras with live ready state from MediaMTX."""
    live = {p["name"]: p for p in _api_paths()}
    return [
        {
            "name": cam,
            "ready": bool(live.get(cam, {}).get("ready", False)),
            "tracks": live.get(cam, {}).get("tracks", []),
        }
        for cam in KNOWN_CAMS
    ]


@mcp.tool
def camera_status(name: str = "eufy_cam1") -> dict:
    """Ready state, tracks, and error counters for one camera."""
    if name not in KNOWN_CAMS:
        return {"name": name, "ready": False, "error": "unknown camera"}
    for p in _api_paths():
        if p["name"] == name:
            return {
                "name": name,
                "ready": p.get("ready", False),
                "tracks": p.get("tracks", []),
                "inbound_bytes": p.get("bytesReceived", 0),
                "inbound_frames_in_error": p.get("inboundFramesInError", 0),
            }
    return {"name": name, "ready": False, "error": "not found in MediaMTX"}


@mcp.tool
def snapshot_camera(name: str = "eufy_cam1") -> dict:
    """Capture a single JPEG frame from a camera. Returns the file path."""
    if name not in KNOWN_CAMS:
        return {"name": name, "error": "unknown camera"}
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
    out = SNAP_DIR / f"{name}_{ts}.jpg"
    latest = SNAP_DIR / f"{name}_latest.jpg"
    res = subprocess.run(
        ["ffmpeg", "-y", "-rtsp_transport", "tcp", "-i", f"{MEDIA_MTX_RTSP}/{name}",
         "-vframes", "1", "-update", "1", str(out)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=False,
    )
    if res.returncode == 0 and out.exists():
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(out)
        return {"name": name, "path": str(out), "latest": str(latest)}
    return {"name": name, "error": "ffmpeg capture failed"}


@mcp.tool
def recordings_info() -> dict:
    """Segment count, disk use, and oldest/newest recording (retention visibility)."""
    segs = sorted(REC_DIR.glob("*.mp4")) if REC_DIR.exists() else []
    total = sum(s.stat().st_size for s in segs)
    return {
        "segments": len(segs),
        "bytes": total,
        "oldest": segs[0].name if segs else None,
        "newest": segs[-1].name if segs else None,
        "retention_policy": "managed by recorder.mjs; 7-day default, runtime override not inspected",
    }


def _rec_segments(name: str) -> list[Path]:
    return sorted(REC_DIR.glob(f"{name}_*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)


@mcp.tool
def motion_clips(name: str = "eufy_cam1", limit: int = 10) -> dict:
    """Newest motion-event recordings for one camera (newest first, capped)."""
    if name not in KNOWN_CAMS:
        return {"name": name, "error": "unknown camera"}
    limit = max(1, min(int(limit), 50))
    segs = _rec_segments(name)[:limit]
    return {
        "name": name,
        "count": len(segs),
        "clips": [str(p) for p in segs],
        "bytes": sum(p.stat().st_size for p in segs),
    }


@mcp.tool
def clip_frame(name: str = "eufy_cam1", clip: str = "", t: float = 5.0) -> dict:
    """Extract one JPEG frame at `t` seconds into a motion clip. Returns the file path."""
    if name not in KNOWN_CAMS:
        return {"name": name, "error": "unknown camera"}
    if not clip or Path(clip).name != clip or not clip.endswith(".mp4"):
        return {"name": name, "error": "invalid clip name"}
    if not clip.startswith(f"{name}_"):
        return {"name": name, "error": "clip does not belong to camera"}
    if not math.isfinite(t) or t < 0:
        return {"name": name, "error": "invalid t"}
    src = REC_DIR / clip
    if not src.is_file():
        return {"name": name, "error": "clip not found"}
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAP_DIR / f"{name}_{Path(clip).stem}_t{t:g}.jpg"
    out.unlink(missing_ok=True)
    res = subprocess.run(
        ["ffmpeg", "-y", "-ss", str(t), "-i", str(src), "-frames:v", "1", "-update", "1", str(out)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=False,
    )
    if res.returncode == 0 and out.exists():
        return {"name": name, "path": str(out)}
    return {"name": name, "error": "ffmpeg extraction failed"}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
