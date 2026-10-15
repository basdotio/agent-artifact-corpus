"""Launcher shortcuts (static, dynamic and pinned) from ``dumpsys shortcut``.

Each shortcut becomes an ``app-shortcut://<package>/<id>`` deep link, the form AURA uses; its
first intent is kept so the shortcut can be started with ``am start``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..shell import q

SCHEME = "app-shortcut://"
_START = re.compile(r"ShortcutInfo \{id=(?P<id>.*?), flags=")
_FIELD = re.compile(r"^\s*(packageName|shortLabel|longLabel|disabledReason)=(.*)$")
_INTENT = re.compile(r"intents=\[Intent \{ (?P<body>.*?) \}")
_PART = re.compile(r"\b(act|dat|cmp|cat|typ)=(\S+)")


@dataclass(frozen=True)
class Shortcut:
    package: str
    id: str
    label: str
    action: str = ""
    data: str = ""
    component: str = ""
    categories: tuple[str, ...] = ()
    enabled: bool = True

    @property
    def uri(self) -> str:
        return f"{SCHEME}{self.package}/{self.id}"

    @property
    def truncated(self) -> bool:
        """dumpsys elides the path of http(s) data URIs ("https://host/...")."""
        return self.data.endswith("/...")

    def am_args(self) -> str:
        args = []
        if self.action:
            args.append(f"-a {q(self.action)}")
        if self.data and not self.truncated:
            args.append(f"-d {q(self.data)}")
        args += [f"-c {q(c)}" for c in self.categories]
        if self.component:
            args.append(f"-n {q(self.component)}")
        elif self.package:
            args.append(f"-p {q(self.package)}")
        return " ".join(args)

    def to_dict(self) -> dict[str, object]:
        return {
            "uri": self.uri,
            "label": self.label,
            "source": "shortcut",
            "intent": {
                k: v
                for k, v in (
                    ("action", self.action),
                    ("data", self.data),
                    ("component", self.component),
                )
                if v
            },
            "enabled": self.enabled,
            **({"intent_data_elided": True} if self.truncated else {}),
        }


def _label(value: str) -> str:
    text = value.split(", resId=")[0].strip()
    return "" if text == "null" else text


def _finish(cur: dict | None, out: list[Shortcut]) -> None:
    if not cur or not cur.get("package") or not cur.get("intent"):
        return
    parts: dict[str, list[str]] = {}
    for key, value in _PART.findall(cur["intent"]):
        parts.setdefault(key, []).append(value)
    comp = (parts.get("cmp") or [""])[0]
    if comp and "/" in comp and comp.split("/", 1)[1].startswith("."):
        pkg, cls = comp.split("/", 1)
        comp = f"{pkg}/{pkg}{cls}"
    out.append(
        Shortcut(
            package=cur["package"],
            id=cur["id"],
            label=cur.get("short") or cur.get("long") or cur["id"],
            action=(parts.get("act") or [""])[0],
            data=(parts.get("dat") or [""])[0],
            component=comp,
            categories=tuple(
                c for v in parts.get("cat", []) for c in v.strip("{}").split(",") if c
            ),
            enabled=cur.get("disabled", "[Not disabled]") == "[Not disabled]",
        )
    )


def parse_shortcuts(dump: str, package: str | None = None) -> list[Shortcut]:
    out: list[Shortcut] = []
    cur: dict | None = None
    for line in dump.splitlines():
        start = _START.search(line)
        if start:
            _finish(cur, out)
            cur = {"id": start.group("id")}
            continue
        if cur is None:
            continue
        field = _FIELD.match(line)
        if field:
            key, value = field.groups()
            if key == "packageName":
                cur["package"] = value.strip()
            elif key == "shortLabel":
                cur["short"] = _label(value)
            elif key == "longLabel":
                cur["long"] = _label(value)
            else:
                cur["disabled"] = value.strip()
            continue
        intent = _INTENT.search(line)
        if intent and "intent" not in cur:
            cur["intent"] = intent.group("body")
    _finish(cur, out)
    seen: set[str] = set()
    unique = []
    for s in out:
        if (package is None or s.package == package) and s.uri not in seen:
            seen.add(s.uri)
            unique.append(s)
    return unique


def split_uri(uri: str) -> tuple[str, str] | None:
    """``app-shortcut://pkg/id`` -> (pkg, id)."""
    if not uri.startswith(SCHEME):
        return None
    rest = uri[len(SCHEME) :]
    if "/" not in rest:
        return None
    pkg, sid = rest.split("/", 1)
    return pkg, sid
