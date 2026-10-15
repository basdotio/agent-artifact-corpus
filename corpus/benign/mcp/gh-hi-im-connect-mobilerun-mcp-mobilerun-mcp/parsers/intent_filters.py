"""Parse the Activity Resolver Table of ``dumpsys package <pkg>`` into deep-link candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

VIEW = "android.intent.action.VIEW"
BROWSABLE = "android.intent.category.BROWSABLE"
DEFAULT = "android.intent.category.DEFAULT"

_HEADER = re.compile(r"^\s+[0-9a-f]+ (\S+/\S+) filter ([0-9a-f]+)\s*$")
_MATCHER = re.compile(r"PatternMatcher\{(LITERAL|PREFIX|SUFFIX|GLOB|ADVANCED_GLOB): (.*)\}$")
_MATCHER_KIND = {"LITERAL": "exact", "PREFIX": "prefix"}
_ITEM = re.compile(r'^\s+(Action|Category|Scheme|Authority|Path|PathPrefix|PathPattern): "(.*?)"')
MAX_LINKS = 40


@dataclass
class IntentFilter:
    component: str
    filter_id: str
    actions: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    schemes: list[str] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)
    paths: list[tuple[str, str]] = field(default_factory=list)  # (kind, value)


@dataclass(frozen=True)
class DeepLink:
    uri: str
    component: str
    kind: str  # exact | prefix | pattern | scheme
    browsable: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "uri": self.uri,
            "component": self.component,
            "kind": self.kind,
            "browsable": self.browsable,
        }


def parse_activity_filters(dump: str) -> list[IntentFilter]:
    """Distinct filters from the Activity Resolver Table (a filter repeats under many keys)."""
    filters: dict[tuple[str, str], IntentFilter] = {}
    current: IntentFilter | None = None
    fresh = False
    in_table = False
    for line in dump.splitlines():
        if line.startswith("Activity Resolver Table:"):
            in_table = True
            continue
        if not in_table:
            continue
        if line and not line.startswith(" "):
            break  # next top-level section
        if m := _HEADER.match(line):
            key = (m.group(1), m.group(2))
            fresh = key not in filters
            current = filters.setdefault(key, IntentFilter(m.group(1), m.group(2)))
        elif current is not None and fresh and (item := _ITEM.match(line)):
            kind, value = item.groups()
            if kind == "Action":
                current.actions.append(value)
            elif kind == "Category":
                current.categories.append(value)
            elif kind == "Scheme":
                current.schemes.append(value)
            elif kind == "Authority":
                current.hosts.append(value)
            else:
                default_kind = {"Path": "exact", "PathPrefix": "prefix"}.get(kind, "pattern")
                if matcher := _MATCHER.match(value):
                    default_kind = _MATCHER_KIND.get(matcher.group(1), "pattern")
                    value = matcher.group(2)
                current.paths.append((default_kind, value))
    return list(filters.values())


def deeplinks_from_filters(filters: list[IntentFilter]) -> list[DeepLink]:
    links: list[DeepLink] = []
    seen: set[str] = set()

    def add(uri: str, component: str, kind: str, browsable: bool) -> None:
        if uri not in seen and len(links) < MAX_LINKS:
            seen.add(uri)
            links.append(DeepLink(uri, component, kind, browsable))

    for flt in filters:
        if VIEW not in flt.actions or not flt.schemes:
            continue
        if BROWSABLE not in flt.categories and DEFAULT not in flt.categories:
            continue
        browsable = BROWSABLE in flt.categories
        for scheme in flt.schemes:
            hosts = flt.hosts or [""]
            for host in hosts:
                base = f"{scheme}://{host}"
                if not flt.paths:
                    add(base if host else f"{scheme}://", flt.component, "scheme", browsable)
                for kind, path in flt.paths:
                    add(f"{base}{path}", flt.component, kind, browsable)
    return links
