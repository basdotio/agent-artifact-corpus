"""One XDG-compliant, pyproject-like configuration document."""

from __future__ import annotations

import copy
import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_IDENTIFIER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$")
_SCHEMA_VERSION = 1


class ConfigError(ValueError):
    """Raised when the local MCP document cannot be resolved."""


def validate_identifier(value: str, *, field: str) -> str:
    if not _IDENTIFIER.fullmatch(value) or ".." in value:
        raise ConfigError(
            f"{field} must be 1-128 letters, numbers, dots, underscores, or dashes and must not contain '..'"
        )
    return value


@dataclass(frozen=True)
class XDGDirectories:
    config: Path
    state: Path
    cache: Path

    @classmethod
    def from_environment(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        home: Path | None = None,
    ) -> XDGDirectories:
        source = os.environ if env is None else env
        resolved_home = Path.home() if home is None else home
        return cls(
            config=_base_path(source.get("XDG_CONFIG_HOME"), resolved_home / ".config"),
            state=_base_path(source.get("XDG_STATE_HOME"), resolved_home / ".local" / "state"),
            cache=_base_path(source.get("XDG_CACHE_HOME"), resolved_home / ".cache"),
        )


@dataclass(frozen=True)
class LocalMCPPaths:
    """Shared document paths plus isolated per-server state paths."""

    xdg: XDGDirectories
    root_name: str = "localmcp"

    def __post_init__(self) -> None:
        validate_identifier(self.root_name, field="root name")

    @classmethod
    def from_environment(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        home: Path | None = None,
        root_name: str = "localmcp",
    ) -> LocalMCPPaths:
        return cls(XDGDirectories.from_environment(env, home=home), root_name=root_name)

    @property
    def config_dir(self) -> Path:
        return self.xdg.config / self.root_name

    @property
    def config_file(self) -> Path:
        return self.config_dir / "localmcp.toml"

    @property
    def state_dir(self) -> Path:
        return self.xdg.state / self.root_name

    @property
    def cache_dir(self) -> Path:
        return self.xdg.cache / self.root_name

    def server_state_dir(self, server: str) -> Path:
        validate_identifier(server, field="server")
        return self.state_dir / server

    def server_cache_dir(self, server: str) -> Path:
        validate_identifier(server, field="server")
        return self.cache_dir / server

    def server_log_file(self, server: str) -> Path:
        validate_identifier(server, field="server")
        return self.server_state_dir(server) / "logs" / f"{server}.log"


def _base_path(value: str | None, fallback: Path) -> Path:
    if value and value.strip():
        candidate = Path(value)
        if candidate.is_absolute():
            return candidate
    return fallback


def read_toml(path: Path, *, missing_ok: bool = True) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except FileNotFoundError:
        if missing_ok:
            return {}
        raise ConfigError(f"configuration file does not exist: {path}") from None
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"failed to read configuration file {path}: {exc}") from exc
    return value


def merge_mappings(*layers: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge mappings; later scalars and lists replace earlier ones."""
    merged: dict[str, Any] = {}
    for layer in layers:
        _merge_into(merged, layer)
    return merged


def _merge_into(target: dict[str, Any], layer: Mapping[str, Any]) -> None:
    for key, value in layer.items():
        existing = target.get(key)
        if isinstance(existing, dict) and isinstance(value, Mapping):
            _merge_into(existing, value)
        else:
            target[key] = copy.deepcopy(value)


@dataclass(frozen=True)
class ServerConfig:
    """The effective global-plus-server view for one MCP server."""

    name: str
    values: dict[str, Any]


@dataclass(frozen=True)
class ConfigDocument:
    """Parsed `localmcp.toml` with per-MCP-server composition.

    All root tables except ``server`` are global defaults. A
    ``[server.<name>...]`` tree deep-merges over those defaults for that server.
    Unknown application keys are deliberately retained for the consuming
    application's schema to validate.
    """

    path: Path
    values: dict[str, Any]

    @classmethod
    def load(
        cls,
        *,
        config_path: Path | None = None,
        env: Mapping[str, str] | None = None,
        home: Path | None = None,
        missing_ok: bool = True,
    ) -> ConfigDocument:
        resolved = config_path or LocalMCPPaths.from_environment(env, home=home).config_file
        values = read_toml(resolved, missing_ok=missing_ok)
        if "tool" in values:
            raise ConfigError("root 'tool' table is no longer supported; use 'server' instead")
        version = values.get("schema_version", _SCHEMA_VERSION)
        if isinstance(version, bool) or not isinstance(version, int):
            raise ConfigError("schema_version must be an integer")
        if version != _SCHEMA_VERSION:
            raise ConfigError(f"unsupported localmcp schema_version {version}; expected {_SCHEMA_VERSION}")
        server_table = values.get("server", {})
        if not isinstance(server_table, dict):
            raise ConfigError("server must be a TOML table")
        return cls(path=resolved, values=values)

    @property
    def global_values(self) -> dict[str, Any]:
        return {key: copy.deepcopy(value) for key, value in self.values.items() if key != "server"}

    @property
    def server_names(self) -> tuple[str, ...]:
        servers = self.values.get("server", {})
        assert isinstance(servers, dict)
        return tuple(sorted(servers))

    def for_server(self, name: str) -> ServerConfig:
        validate_identifier(name, field="server")
        servers = self.values.get("server", {})
        assert isinstance(servers, dict)
        overlay = servers.get(name, {})
        if not isinstance(overlay, Mapping):
            raise ConfigError(f"server.{name} must be a TOML table")
        return ServerConfig(name=name, values=merge_mappings(self.global_values, overlay))

    def secret_mappings(self, server: str | None = None) -> dict[str, dict[str, Any]]:
        """Return composed secret declarations without resolving any values."""
        global_secrets = _mapping_table(self.global_values.get("secrets", {}), field="secrets")
        composed = {name: copy.deepcopy(dict(value)) for name, value in global_secrets.items()}
        if server is None:
            return composed

        validate_identifier(server, field="server")
        servers = self.values.get("server", {})
        assert isinstance(servers, dict)
        raw_server = servers.get(server, {})
        if not isinstance(raw_server, Mapping):
            raise ConfigError(f"server.{server} must be a TOML table")
        server_secrets = _mapping_table(raw_server.get("secrets", {}), field=f"server.{server}.secrets")
        for name, value in server_secrets.items():
            if name in composed:
                composed[name] = merge_mappings(composed[name], value)
            else:
                composed[name] = copy.deepcopy(dict(value))
        return composed


def _mapping_table(value: Any, *, field: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"{field} must be a TOML table")
    result: dict[str, Mapping[str, Any]] = {}
    for name, item in value.items():
        validate_identifier(str(name), field=f"{field} name")
        if not isinstance(item, Mapping):
            raise ConfigError(f"{field}.{name} must be a TOML table")
        result[str(name)] = item
    return result
