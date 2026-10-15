"""Device configuration loading (YAML) with environment variable expansion."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .platforms import PLATFORMS

ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

APP_CONFIG_DIR = Path.home() / ".config" / "mcp-llmnetops"

VALID_KNOWN_HOSTS = ("auto", "strict", "no-check")


@dataclass
class DeviceConfig:
    """Connection settings for a single network device."""

    name: str
    host: str
    platform: str
    username: str
    password: str | None = None
    port: int = 22
    ssh_key: str | None = None
    timeout: float = 60.0
    known_hosts: str = "auto"  # auto | strict | no-check

    @property
    def platform_def(self):
        return PLATFORMS[self.platform]


def _expand_env(value: Any) -> Any:
    """Expand ${VAR} references in string values from the environment."""
    if isinstance(value, str):
        return ENV_VAR_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)
    return value


def _default_config_paths() -> list[Path]:
    return [
        Path.cwd() / "devices.yaml",
        Path.cwd() / "devices.yml",
        APP_CONFIG_DIR / "devices.yaml",
        APP_CONFIG_DIR / "devices.yml",
    ]


def resolve_config_path(explicit: str | None = None) -> Path | None:
    """Resolve the config file path from arg, env var, or default locations."""
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.exists() else None
    env = os.environ.get("MCP_LLMNETOPS_CONFIG")
    if env:
        p = Path(env).expanduser()
        return p if p.exists() else None
    for p in _default_config_paths():
        if p.exists():
            return p
    return None


def load_devices(config_path: str | Path | None = None) -> dict[str, DeviceConfig]:
    """Load and validate device definitions. Returns {name: DeviceConfig}."""
    path = Path(config_path).expanduser() if config_path else resolve_config_path()
    if path is None:
        return {}
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    devices: dict[str, DeviceConfig] = {}
    for i, entry in enumerate(data.get("devices") or []):
        if not isinstance(entry, dict):
            raise ValueError(f"devices[{i}]: expected a mapping")
        entry = {k: _expand_env(v) for k, v in entry.items()}

        for required in ("name", "host", "platform", "username"):
            if not entry.get(required):
                raise ValueError(f"devices[{i}]: missing required field '{required}'")

        name = str(entry["name"])
        platform = str(entry["platform"])
        if platform not in PLATFORMS:
            raise ValueError(
                f"Device '{name}': unknown platform '{platform}'. "
                f"Valid platforms: {', '.join(sorted(PLATFORMS))}"
            )

        known_hosts = str(entry.get("known_hosts", "auto"))
        if known_hosts not in VALID_KNOWN_HOSTS:
            raise ValueError(
                f"Device '{name}': invalid known_hosts '{known_hosts}'. "
                f"Valid values: {', '.join(VALID_KNOWN_HOSTS)}"
            )

        if not entry.get("password") and not entry.get("ssh_key"):
            raise ValueError(f"Device '{name}': either 'password' or 'ssh_key' is required")

        if name in devices:
            raise ValueError(f"Duplicate device name: '{name}'")

        devices[name] = DeviceConfig(
            name=name,
            host=str(entry["host"]),
            platform=platform,
            username=str(entry["username"]),
            password=entry.get("password") or None,
            port=int(entry.get("port", 22)),
            ssh_key=entry.get("ssh_key"),
            timeout=float(entry.get("timeout", 60)),
            known_hosts=known_hosts,
        )
    return devices