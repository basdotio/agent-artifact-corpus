"""Installed-app models and name matching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

MIN_SCORE = 0.5
CONFIDENT_GAP = 0.1


@dataclass(frozen=True)
class App:
    package: str
    label: str
    system: bool = False
    version: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "package": self.package,
            "label": self.label,
            "system": self.system,
            # mobilerun-core list_apps field names
            "package_name": self.package,
            "version_name": self.version,
            "is_system_app": self.system,
        }


def parse_apps(raw: list[dict[str, Any]]) -> list[App]:
    return [
        App(
            package=str(item.get("packageName", "")),
            label=str(item.get("label", "")),
            system=bool(item.get("isSystemApp")),
            version=str(item.get("versionName", "")),
        )
        for item in raw
        if item.get("packageName")
    ]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", text.lower()).strip()


def score(query: str, app: App) -> float:
    q, label, pkg = _norm(query), _norm(app.label), app.package.lower()
    if not q:
        return 0.0
    if q == label or query.strip().lower() == pkg:
        return 1.0
    if label.startswith(q):
        return 0.92
    if any(word.startswith(q) for word in label.split()):
        return 0.85
    if q in label:
        return 0.75
    if q in pkg.split("."):
        return 0.7
    if q in pkg:
        return 0.65
    ratio = SequenceMatcher(None, q, label).ratio()
    return round(ratio * 0.6, 3) if ratio >= MIN_SCORE else 0.0


def rank_apps(query: str, apps: list[App], limit: int = 5) -> list[tuple[App, float]]:
    scored = [(app, score(query, app)) for app in apps]
    ranked = sorted((s for s in scored if s[1] >= MIN_SCORE), key=lambda s: (-s[1], s[0].label))
    return ranked[:limit]


def resolve_app(query: str, apps: list[App]) -> tuple[App | None, list[tuple[App, float]]]:
    """Best app when unambiguous, plus the ranked candidates."""
    ranked = rank_apps(query, apps)
    if not ranked:
        return None, []
    best, best_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    if best_score >= 0.85 and best_score - runner_up >= CONFIDENT_GAP:
        return best, ranked
    if best_score == 1.0 and runner_up < 1.0:
        return best, ranked
    return None, ranked
