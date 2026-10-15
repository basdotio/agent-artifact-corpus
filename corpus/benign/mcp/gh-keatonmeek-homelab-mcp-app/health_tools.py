"""Bounded read-only access to a fixed, host-produced health snapshot."""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
import stat
from typing import Literal

MAX_BYTES = 262144
Section = Literal["summary", "system", "docker", "storage", "logs", "network"]


async def read_health(snapshot: Path, section: Section = "summary") -> dict:
    """No host commands run here. The configured snapshot is the sole data source."""
    try:
        descriptor = os.open(snapshot, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError()
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError()
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError()
        collected = datetime.datetime.fromisoformat(data["collected_at"])
        if collected.tzinfo is None:
            raise ValueError()
        now = datetime.datetime.now(datetime.timezone.utc)
        age = (now - collected).total_seconds()
        if age < -60:
            raise ValueError()
        age = max(0, age)
        result = {"available": True, "collected_at": data["collected_at"],
                  "age_seconds": round(age, 1), "stale": age > 180}
        if section == "summary":
            docker = data.get("docker", {})
            system = data.get("system", {})
            containers = docker.get("containers", [])
            result["summary"] = {
                "hostname": system.get("hostname"), "uptime_seconds": system.get("uptime_seconds"),
                "load_1_5_15": system.get("load_1_5_15"), "memory_bytes": system.get("memory_bytes"),
                "failed_units": system.get("failed_units"), "docker_available": docker.get("available"),
                "container_count": len(containers),
                "container_attention": [
                    {key: item.get(key) for key in ("name", "state", "health", "restart_count")}
                    for item in containers if item.get("state") != "running"
                    or item.get("health") == "unhealthy" or item.get("oom_killed")
                ],
                "storage": data.get("storage", []), "recent_errors": data.get("logs"),
            }
        else:
            result[section] = data.get(section)
        return result
    except (OSError, ValueError, KeyError, TypeError, AttributeError, UnicodeError):
        return {"available": False, "error": "snapshot_unavailable_or_invalid"}


def register(server, snapshot: Path) -> None:
    async def health(section: Section = "summary") -> dict:
        """Read the configured sanitized host-health snapshot. No host commands or raw logs are requested. Collection time, age, and a stale flag are returned; availability and freshness depend on an independently configured collector."""
        return await read_health(snapshot, section)

    server.tool(health, annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False})
