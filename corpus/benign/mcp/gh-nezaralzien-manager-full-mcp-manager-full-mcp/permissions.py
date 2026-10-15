"""Permission matrix: what this MCP may do, per business, per resource, per op.

Two sources, in order:

1. The control panel file (`~/.manager-full-mcp/permissions/<business>.json`),
   written by the tick-box panel. Authoritative when it exists.
2. Extension defaults from env (the checkboxes in the Claude Desktop extension
   settings), applied at group level, used until a panel file exists.

`MANAGER_FULL_READ_ONLY=true` overrides both and disables every write.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from manager_full_mcp.catalog import (
    GROUP_ORDER,
    HIGH_RISK_GROUPS,
    OPS,
    Catalog,
    Resource,
)
from manager_full_mcp.config import permissions_file, write_private_json

SOURCE_PANEL = "control-panel"
SOURCE_DEFAULTS = "extension-defaults"

# Three states per resource and operation.
ALLOW = "allow"
ASK = "ask"  # allowed, but only after the user confirms in a dialog
DENY = "deny"
MODES = (ALLOW, ASK, DENY)

DEFAULT_DEFAULTS: dict[str, str] = {
    "read": ALLOW,
    "create": DENY,
    "update": DENY,
    "delete": DENY,
}


def coerce_mode(value: object, fallback: str = DENY) -> str:
    """Accept 'allow'/'ask'/'deny' and the booleans older files used."""
    if isinstance(value, bool):
        return ALLOW if value else DENY
    if isinstance(value, str) and value.casefold() in MODES:
        return value.casefold()
    return fallback


def _env_bool(name: str, fallback: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return fallback
    return raw.strip().casefold() in {"1", "true", "yes", "on", "allow", "allowed"}


def _env_csv(name: str) -> set[str]:
    raw = os.environ.get(name, "")
    return {t.strip().casefold().replace("-", "_") for t in raw.split(",") if t.strip()}


def read_only_override() -> bool:
    return _env_bool("MANAGER_FULL_READ_ONLY", False)


def env_group_grants() -> dict[str, dict[str, str]]:
    """Group-level grants from the extension checkboxes.

    A ticked box on a high-risk group means *ask first*, never silent access:
    the fine-grained "always allow" for those lives in the control panel.
    """
    write_csv = _env_csv("MANAGER_FULL_WRITE_GROUPS")
    delete_csv = _env_csv("MANAGER_FULL_DELETE_GROUPS")
    read_all = _env_bool("MANAGER_FULL_READ_ALL", True)
    grants: dict[str, dict[str, str]] = {}
    for group in GROUP_ORDER:
        upper = group.upper()
        ticked = ASK if group in HIGH_RISK_GROUPS else ALLOW
        write = ticked if _env_bool(f"MANAGER_FULL_WRITE_{upper}", group in write_csv) else DENY
        delete = ticked if _env_bool(f"MANAGER_FULL_DELETE_{upper}", group in delete_csv) else DENY
        grants[group] = {
            "read": ALLOW if read_all else DENY,
            "create": write,
            "update": write,
            "delete": delete,
        }
    return grants


@dataclass
class Policy:
    """Effective permissions for one business."""

    business_id: str
    source: str = SOURCE_DEFAULTS
    defaults: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_DEFAULTS))
    resources: dict[str, dict[str, str]] = field(default_factory=dict)
    raw_read: bool = True
    raw_write: bool = False
    updated_at: str = ""
    read_only: bool = False
    mtime: float = 0.0

    def grants_for(self, resource: Resource) -> dict[str, str]:
        explicit = self.resources.get(resource.name) or {}
        out: dict[str, str] = {}
        for op in OPS:
            if not resource.supports(op) or (resource.locked and op != "read"):
                out[op] = DENY
                continue
            mode = coerce_mode(
                explicit.get(op, self.defaults.get(op, DENY)),
                fallback=coerce_mode(self.defaults.get(op, DENY)),
            )
            if self.read_only and op != "read":
                mode = DENY
            out[op] = mode
        return out

    def decide(self, resource: Resource, op: str) -> str:
        """'allow', 'ask' (confirm with the user first) or 'deny'."""
        return self.grants_for(resource).get(op, DENY)

    def allows(self, resource: Resource, op: str) -> bool:
        return self.decide(resource, op) == ALLOW

    def denial_reason(self, resource: Resource, op: str) -> str:
        if not resource.supports(op):
            return (
                f"'{resource.name}' does not support {op} in this Manager instance."
            )
        if resource.locked and op != "read":
            return (
                f"'{resource.name}' is account-security data; writes are permanently "
                "blocked in this server. Change it inside Manager directly."
            )
        if self.read_only:
            return (
                "This connection is in read-only mode "
                "(MANAGER_FULL_READ_ONLY=true); no writes are possible."
            )
        where = (
            "the control panel"
            if self.source == SOURCE_PANEL
            else "the extension settings checkboxes"
        )
        return (
            f"Not permitted: '{op}' on '{resource.name}' is unticked. "
            f"Tick it in {where} (ask me to open the permissions panel), then retry."
        )

    def matrix(self, catalog: Catalog) -> dict[str, dict[str, str]]:
        return {name: self.grants_for(res) for name, res in catalog.resources.items()}

    def summary(self, catalog: Catalog) -> dict[str, Any]:
        counts = {op: 0 for op in OPS}
        ask_counts = {op: 0 for op in OPS}
        supported = {op: 0 for op in OPS}
        for res in catalog.resources.values():
            grants = self.grants_for(res)
            for op in OPS:
                if res.supports(op) and not (res.locked and op != "read"):
                    supported[op] += 1
                if grants[op] == ALLOW:
                    counts[op] += 1
                elif grants[op] == ASK:
                    ask_counts[op] += 1
        return {
            "business": self.business_id,
            "source": self.source,
            "read_only_mode": self.read_only,
            "allowed": counts,
            "ask_first": ask_counts,
            "available": supported,
            "raw_read": self.raw_read,
            "raw_write": self.raw_write and not self.read_only,
            "updated_at": self.updated_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "business": self.business_id,
            "updated_at": self.updated_at or time.strftime("%Y-%m-%dT%H:%M:%S"),
            "defaults": self.defaults,
            "raw_read": self.raw_read,
            "raw_write": self.raw_write,
            "resources": self.resources,
        }


def policy_from_env(business_id: str, catalog: Catalog) -> Policy:
    grants = env_group_grants()
    resources = {
        name: dict(grants.get(res.group, DEFAULT_DEFAULTS))
        for name, res in catalog.resources.items()
    }
    return Policy(
        business_id=business_id,
        source=SOURCE_DEFAULTS,
        defaults=dict(DEFAULT_DEFAULTS),
        resources=resources,
        raw_read=_env_bool("MANAGER_FULL_RAW_READ", True),
        raw_write=_env_bool("MANAGER_FULL_RAW_WRITE", False),
        read_only=read_only_override(),
    )


def load_policy(business_id: str, catalog: Catalog) -> Policy:
    path = permissions_file(business_id)
    if not path.is_file():
        return policy_from_env(business_id, catalog)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return policy_from_env(business_id, catalog)
    defaults = {
        op: coerce_mode((raw.get("defaults") or {}).get(op, DEFAULT_DEFAULTS[op]),
                        fallback=DEFAULT_DEFAULTS[op])
        for op in OPS
    }
    resources = {
        name: {
            op: coerce_mode(value.get(op, defaults.get(op, DENY))) for op in OPS
        }
        for name, value in (raw.get("resources") or {}).items()
        if isinstance(value, dict)
    }
    return Policy(
        business_id=business_id,
        source=SOURCE_PANEL,
        defaults=defaults,
        resources=resources,
        raw_read=bool(raw.get("raw_read", True)),
        raw_write=bool(raw.get("raw_write", False)),
        updated_at=str(raw.get("updated_at", "")),
        read_only=read_only_override(),
        mtime=path.stat().st_mtime,
    )


def save_policy(policy: Policy) -> None:
    policy.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    write_private_json(permissions_file(policy.business_id), policy.to_dict())


def policy_is_stale(policy: Policy) -> bool:
    """True when the panel wrote a new file since this policy was loaded."""
    path = permissions_file(policy.business_id)
    if not path.is_file():
        return policy.source == SOURCE_PANEL
    return path.stat().st_mtime != policy.mtime
