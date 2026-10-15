"""Small parsers for assorted ``adb shell`` outputs (device status, contacts, resolve, files)."""

from __future__ import annotations

import re
from dataclasses import dataclass


def parse_battery(dump: str) -> dict[str, object]:
    info: dict[str, object] = {}
    for line in dump.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.strip().partition(":")
        value = value.strip()
        if key in ("level", "scale", "status", "health", "temperature", "voltage"):
            if value.lstrip("-").isdigit():
                info[key] = int(value)
        elif key in ("AC powered", "USB powered", "Wireless powered", "present"):
            info[key.lower().replace(" ", "_")] = value == "true"
    return info


def parse_wm_size(output: str) -> tuple[int, int] | None:
    matches = re.findall(r"(\d+)x(\d+)", output)
    if not matches:
        return None
    width, height = matches[-1]  # an "Override size" line, when present, comes last
    return int(width), int(height)


def parse_wm_density(output: str) -> int | None:
    matches = re.findall(r"density: (\d+)", output)
    return int(matches[-1]) if matches else None


def parse_getprop(output: str) -> dict[str, str]:
    return dict(re.findall(r"^\[([^\]]+)\]: \[(.*)\]$", output, flags=re.M))


def parse_wakefulness(output: str) -> str:
    m = re.search(r"mWakefulness=(\w+)", output)
    return m.group(1).lower() if m else "unknown"


def parse_focus(output: str) -> tuple[str, str] | None:
    """(package, activity) from a ``mCurrentFocus=Window{... u0 pkg/activity}`` line."""
    m = re.search(r"mCurrentFocus=Window\{\S+ u\d+ ([\w.]+)/([\w.$]+)\}", output)
    return (m.group(1), m.group(2)) if m else None


def parse_df(output: str) -> dict[str, int] | None:
    lines = [ln for ln in output.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    parts = lines[-1].split()
    if len(parts) < 5 or not parts[1].isdigit():
        return None
    total, used, free = int(parts[1]), int(parts[2]), int(parts[3])
    return {"total_kb": total, "used_kb": used, "free_kb": free}


def parse_ip_addresses(output: str) -> list[str]:
    return [
        a for a in re.findall(r"inet (\d+\.\d+\.\d+\.\d+)/", output) if not a.startswith("127.")
    ]


@dataclass(frozen=True)
class Contact:
    name: str
    number: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "number": self.number}


_CONTACT_ROW = re.compile(r"^Row: \d+ display_name=(?P<name>.*?), data1=(?P<number>.*)$")


def parse_contacts(output: str) -> list[Contact]:
    contacts = []
    for line in output.splitlines():
        if m := _CONTACT_ROW.match(line.strip()):
            contacts.append(Contact(m.group("name"), m.group("number")))
    return contacts


def parse_resolve_activity(output: str) -> str | None:
    """Component (``pkg/.Activity``) from ``cmd package resolve-activity --brief``; None if unresolved."""
    for line in output.splitlines():
        line = line.strip()
        if re.fullmatch(r"[\w.]+/[\w.$]+", line):
            return line
    return None


def parse_devtools_sockets(output: str) -> list[tuple[str, int | None]]:
    """(socket name, pid) for each ``@*devtools_remote*`` abstract socket."""
    found = []
    for name in sorted(set(re.findall(r"@([a-z_]*devtools_remote[_0-9a-z]*)", output))):
        pid = re.search(r"_(\d+)$", name)
        found.append((name, int(pid.group(1)) if pid else None))
    return found


def parse_find(output: str) -> list[str]:
    return [ln.strip() for ln in output.splitlines() if ln.strip().startswith("/")]


def is_chooser(component: str | None) -> bool:
    """True for the system resolver/chooser, i.e. no single default handler exists."""
    return bool(component) and component.startswith("android/com.android.internal.app.")


MEDIA_KINDS = {"1": "image", "2": "audio", "3": "video", "6": "document"}
MEDIA_COLLECTION = {"image": "images", "audio": "audio", "video": "video"}
_ROW = re.compile(r"^Row: \d+ (.*)$")


def parse_content_rows(raw: str, keys: tuple[str, ...]) -> list[dict[str, str]]:
    """``content query`` rows; values may contain ", " so fields are split on the known keys."""
    rows = []
    pattern = re.compile(r"(?:^|, )(" + "|".join(map(re.escape, keys)) + r")=")
    for line in raw.splitlines():
        m = _ROW.match(line.strip())
        if not m:
            continue
        body = m.group(1)
        marks = list(pattern.finditer(body))
        row = {}
        for i, mk in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
            value = body[mk.end() : end]
            row[mk.group(1)] = "" if value == "NULL" else value
        rows.append(row)
    return rows


def media_uri(row: dict[str, str]) -> str:
    kind = MEDIA_KINDS.get(row.get("media_type", ""), "")
    collection = MEDIA_COLLECTION.get(kind)
    if collection:
        return f"content://media/external/{collection}/media/{row['_id']}"
    return f"content://media/external/file/{row['_id']}"
