"""Parse ``dumpsys media_session`` and ``cmd media_session volume`` output."""

from __future__ import annotations

import re
from dataclasses import dataclass

STATE_NAMES = {
    0: "none",
    1: "stopped",
    2: "paused",
    3: "playing",
    4: "fast_forwarding",
    5: "rewinding",
    6: "buffering",
    7: "error",
    8: "connecting",
    9: "skipping_to_previous",
    10: "skipping_to_next",
    11: "skipping_to_queue_item",
}
_SESSION = re.compile(r"^ {2}(\S+) (\S+)/(\S+) \(userId=(\d+)\)$")
_STATE = re.compile(r"^ {4}state=PlaybackState \{state=(?:\w+\()?(\d+)\)?")
_METADATA = re.compile(r"^ {4}metadata: (?:size=\d+, description=)?(.*)$")
_VOLUME_GET = re.compile(r"volume is (\d+) in range \[(\d+)\.\.(\d+)\]")


@dataclass(frozen=True)
class MediaSession:
    tag: str
    package: str
    active: bool
    state: str
    description: str
    system: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "tag": self.tag,
            "package": self.package,
            "active": self.active,
            "state": self.state,
            "description": self.description,
        }


def parse_media_sessions(dump: str, include_system: bool = False) -> list[MediaSession]:
    sessions: list[MediaSession] = []
    current: dict[str, object] | None = None

    def flush() -> None:
        if current is None:
            return
        package = str(current["package"])
        system = package.startswith(("android", "com.android.server"))
        if system and not include_system:
            return
        sessions.append(
            MediaSession(
                tag=str(current["tag"]),
                package=package,
                active=bool(current.get("active")),
                state=str(current.get("state", "none")),
                description=str(current.get("description", "")),
                system=system,
            )
        )

    for line in dump.splitlines():
        if line.startswith("User Records:"):
            break
        if m := _SESSION.match(line):
            flush()
            current = {"tag": m.group(1), "package": m.group(2)}
        elif current is not None:
            if line.strip().startswith("active="):
                current["active"] = line.strip() == "active=true"
            elif m := _STATE.match(line):
                current["state"] = STATE_NAMES.get(int(m.group(1)), "unknown")
            elif m := _METADATA.match(line):
                value = m.group(1)
                current["description"] = "" if value == "null" else value
    flush()
    return sessions


def parse_volume_get(output: str) -> tuple[int, int, int] | None:
    """(current, min, max) from ``cmd media_session volume --get``."""
    m = _VOLUME_GET.search(output)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def parse_stream_block(dump: str, stream: str = "STREAM_MUSIC") -> dict[str, object]:
    """Volume/mute for one stream from ``dumpsys audio``."""
    lines = dump.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == f"- {stream}:")
    except StopIteration:
        return {}
    info: dict[str, object] = {}
    for ln in lines[start + 1 : start + 12]:
        stripped = ln.strip()
        if stripped.startswith("- "):
            break
        if stripped.startswith("Muted:"):
            info["muted"] = stripped.split(":", 1)[1].strip() == "true"
        elif stripped.startswith("Min:"):
            info["min"] = int(stripped.split(":", 1)[1])
        elif stripped.startswith("Max:"):
            info["max"] = int(stripped.split(":", 1)[1])
        elif stripped.startswith("streamVolume:"):
            info["volume"] = int(stripped.split(":", 1)[1])
    return info
