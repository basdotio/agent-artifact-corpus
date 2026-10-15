"""Config home, business registry, and catalog cache.

One installation serves any number of Manager businesses. Each business is a
name + API URL + access token, added through the local control panel (never
through chat), and carries its own permission file and catalog cache.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from manager_full_mcp.catalog import Catalog

HOME_ENV = "MANAGER_FULL_HOME"
CATALOG_TTL_SECONDS = 24 * 3600


def home() -> Path:
    raw = os.environ.get(HOME_ENV, "").strip()
    path = Path(raw).expanduser() if raw else Path.home() / ".manager-full-mcp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sub_dir(name: str) -> Path:
    path = home() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def businesses_file() -> Path:
    return home() / "businesses.json"


def permissions_file(business_id: str) -> Path:
    return _sub_dir("permissions") / f"{business_id}.json"


def catalog_file(business_id: str) -> Path:
    return _sub_dir("catalog") / f"{business_id}.json"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().casefold()).strip("-")
    return slug or "business"


def write_private_json(path: Path, payload: Any) -> None:
    """Write JSON so only the current user can read it (tokens live here)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    os.chmod(path, 0o600)


@dataclass
class Business:
    id: str
    name: str
    api_url: str
    api_key: str = ""
    enabled: bool = True
    note: str = ""

    def public(self) -> dict[str, Any]:
        """Everything except the token (safe to show in tools and the panel)."""
        return {
            "id": self.id,
            "name": self.name,
            "api_url": self.api_url,
            "enabled": self.enabled,
            "note": self.note,
            "has_key": bool(self.api_key),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "api_url": self.api_url,
            "api_key": self.api_key,
            "enabled": self.enabled,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Business:
        return cls(
            id=raw.get("id") or slugify(raw.get("name", "")),
            name=raw.get("name") or raw.get("id") or "Business",
            api_url=(raw.get("api_url") or "").rstrip("/"),
            api_key=raw.get("api_key") or "",
            enabled=bool(raw.get("enabled", True)),
            note=raw.get("note") or "",
        )


@dataclass
class Registry:
    businesses: list[Business] = field(default_factory=list)

    def get(self, business_id: str) -> Business | None:
        for b in self.businesses:
            if b.id == business_id:
                return b
        return None

    def resolve(self, ref: str | None) -> Business | None:
        """Accept an id, a name, or nothing when only one business exists."""
        active = [b for b in self.businesses if b.enabled]
        if not ref:
            return active[0] if len(active) == 1 else None
        needle = ref.strip().casefold()
        for b in self.businesses:
            if b.id.casefold() == needle or b.name.casefold() == needle:
                return b
        matches = [b for b in self.businesses if needle in b.name.casefold()]
        return matches[0] if len(matches) == 1 else None

    def upsert(self, business: Business) -> None:
        for index, existing in enumerate(self.businesses):
            if existing.id == business.id:
                self.businesses[index] = business
                return
        self.businesses.append(business)

    def remove(self, business_id: str) -> bool:
        before = len(self.businesses)
        self.businesses = [b for b in self.businesses if b.id != business_id]
        return len(self.businesses) != before


def load_registry() -> Registry:
    path = businesses_file()
    if not path.is_file():
        return Registry(businesses=_registry_from_env())
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Registry(businesses=_registry_from_env())
    registry = Registry(
        businesses=[Business.from_dict(b) for b in (raw.get("businesses") or [])]
    )
    if not registry.businesses:
        registry.businesses = _registry_from_env()
    return registry


def save_registry(registry: Registry) -> None:
    write_private_json(
        businesses_file(),
        {
            "version": 1,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "businesses": [b.to_dict() for b in registry.businesses],
        },
    )


def _registry_from_env() -> list[Business]:
    """Single-business bootstrap from env, for a plain mcp.json install."""
    url = os.environ.get("MANAGER_API_URL", "").strip()
    key = os.environ.get("MANAGER_API_KEY", "").strip()
    if not url or not key:
        return []
    name = os.environ.get("MANAGER_BUSINESS_NAME", "").strip() or "Default"
    return [Business(id=slugify(name), name=name, api_url=url.rstrip("/"), api_key=key)]


def load_cached_catalog(business_id: str, *, max_age: int = CATALOG_TTL_SECONDS) -> Catalog | None:
    path = catalog_file(business_id)
    if not path.is_file():
        return None
    if max_age >= 0 and time.time() - path.stat().st_mtime > max_age:
        return None
    try:
        return Catalog.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def save_catalog(business_id: str, catalog: Catalog) -> None:
    path = catalog_file(business_id)
    path.write_text(
        json.dumps(catalog.to_dict(), indent=1, ensure_ascii=False), encoding="utf-8"
    )
