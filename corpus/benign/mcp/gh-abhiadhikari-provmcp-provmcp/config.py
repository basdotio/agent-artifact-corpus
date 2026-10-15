"""servers.yaml — which downstream servers the proxy fronts, and how.

    ledger: ./provenance.jsonl
    servers:
      - id: geo
        command: ["uvx", "geo-mcp"]
        source: geo                  # release resolver, see sources.py
      - id: opentargets
        url: https://example.org/mcp
        source: opentargets
        retention: full              # opt in; default is hash_only
      - id: trials
        command: ["uvx", "clinicaltrials-mcp"]
        source: clinicaltrials
        redact_arguments: [patient_id]

`id` becomes the tool-name prefix the client sees (`geo__search_geo`), and the
`server_id` recorded in every ledger entry, so it must be stable across the life
of a ledger — replay looks servers up by it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class Retention(StrEnum):
    HASH_ONLY = "hash_only"  # default: store sha256 of the result, never the result
    FULL = "full"            # store the result too — opt in per server, never global


@dataclass
class DownstreamServer:
    id: str
    command: list[str] | None = None        # stdio
    url: str | None = None                  # streamable-http
    env: dict[str, str] = field(default_factory=dict)
    source: str | None = None               # key into sources.RESOLVERS
    source_options: dict[str, Any] = field(default_factory=dict)
    retention: Retention = Retention.HASH_ONLY
    redact_arguments: list[str] = field(default_factory=list)
    inproc: Any = None                      # an in-process Server, tests only

    def __post_init__(self) -> None:
        if not self.id or "__" in self.id or self.id == "provmcp":
            raise ValueError(
                f"server id {self.id!r} must be non-empty, not contain '__', and not be 'provmcp'"
            )
        if sum(x is not None for x in (self.command, self.url, self.inproc)) != 1:
            raise ValueError(f"server {self.id!r}: exactly one of command, url required")


@dataclass
class Config:
    servers: list[DownstreamServer]
    ledger: Path = Path("./provenance.jsonl")
    server_log_dir: Path | None = None   # stdio servers' stderr -> <dir>/<id>.stderr.log

    def by_id(self, server_id: str) -> DownstreamServer | None:
        return next((s for s in self.servers if s.id == server_id), None)


def load_config(path: Path | str) -> Config:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    servers = []
    for item in raw.get("servers", []):
        servers.append(
            DownstreamServer(
                id=str(item["id"]),
                command=item.get("command"),
                url=item.get("url"),
                env={k: str(v) for k, v in (item.get("env") or {}).items()},
                source=item.get("source"),
                source_options=item.get("source_options") or {},
                retention=Retention(item.get("retention", "hash_only")),
                redact_arguments=list(item.get("redact_arguments") or []),
            )
        )
    ids = [s.id for s in servers]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate server ids in {path}: {ids}")
    if not servers:
        raise ValueError(f"{path}: no servers configured")
    log_dir = raw.get("server_log_dir")
    return Config(
        servers=servers,
        ledger=Path(raw.get("ledger", "./provenance.jsonl")),
        server_log_dir=Path(log_dir) if log_dir else None,
    )
