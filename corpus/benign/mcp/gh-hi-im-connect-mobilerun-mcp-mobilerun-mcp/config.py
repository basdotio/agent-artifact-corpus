"""Runtime configuration, read once from the environment."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

POLICY_MODES = ("off", "standard", "strict")
ALL_SCOPES = frozenset({"read", "write"})


@dataclass(frozen=True)
class Config:
    device: str = ""  # empty: use the only attached adb device
    policy: str = "off"
    enable_adb: bool = False
    scopes: frozenset[str] = ALL_SCOPES
    adb_bin: str | None = None
    mobilerun_bin: str | None = None
    brave_api_key: str | None = None
    cloud_api_key: str | None = None
    tavily_api_key: str | None = None
    http_host: str = "127.0.0.1"
    http_port: int = 4816

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        env = os.environ if env is None else env
        policy = env.get("MOBILERUN_MCP_POLICY", "off").strip().lower()
        if policy not in POLICY_MODES:
            policy = "off"
        scopes = (
            frozenset(
                s.strip().lower() for s in env.get("MOBILERUN_MCP_SCOPES", "read,write").split(",")
            )
            & ALL_SCOPES
        )
        return cls(
            device=env.get("MOBILERUN_DEVICE", "").strip(),
            policy=policy,
            enable_adb=env.get("MOBILERUN_MCP_ENABLE_ADB", "0").strip() in ("1", "true", "yes"),
            scopes=scopes or ALL_SCOPES,
            adb_bin=env.get("MOBILERUN_ADB_BIN") or None,
            mobilerun_bin=env.get("MOBILERUN_BIN") or None,
            brave_api_key=env.get("BRAVE_API_KEY") or None,
            cloud_api_key=env.get("MOBILERUN_CLOUD_API_KEY") or None,
            tavily_api_key=env.get("TAVILY_API_KEY") or None,
            http_host=env.get("MOBILERUN_MCP_HTTP_HOST", "127.0.0.1").strip() or "127.0.0.1",
            http_port=int(env.get("MOBILERUN_MCP_HTTP_PORT", "4816") or 4816),
        )
